import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.views.decorators.http import require_POST
from django.db import transaction
from django.utils import timezone
import datetime

from habitaciones.models import Habitación, TipoHabitacion
from reservas.models import Reserva, Cliente, Folio, Cargo, Abono
from operaciones.models import TareaLimpieza, OrdenMantenimiento, MensajeContacto
from core.security_validators import validar_politica_contrasena_chile
from core.rut_and_email_validators import validar_documento_identidad, validar_correo_real, validar_telefono_chileno
from core.mfa_service import generar_datos_mfa, validar_codigo_mfa
from core.webpay_service import iniciar_pago_webpay, confirmar_pago_webpay

# ========================================================
# FUNCIONES AUXILIARES DE CONTROL DE ACCESO (RBAC)
# ========================================================

def es_recepcionista(user):
    return user.is_authenticated and (user.groups.filter(name='recepcion').exists() or user.is_superuser)

def es_housekeeping(user):
    return user.is_authenticated and (user.groups.filter(name='housekeeping').exists() or user.is_superuser)

def es_mantenimiento(user):
    return user.is_authenticated and (user.groups.filter(name='mantenimiento').exists() or user.is_superuser)

def obtener_rol_usuario(user):
    if user.is_superuser:
        return 'admin'
    if user.groups.filter(name='recepcion').exists():
        return 'recepcion'
    if user.groups.filter(name='housekeeping').exists():
        return 'housekeeping'
    if user.groups.filter(name='mantenimiento').exists():
        return 'mantenimiento'
    return 'cliente'

def obtener_camarera_disponible():
    staff_aseo = list(User.objects.filter(groups__name='housekeeping').order_by('id'))
    if not staff_aseo:
        return None
    cargas = {u: TareaLimpieza.objects.filter(responsable=u, estado__in=['Pendiente', 'EnProceso']).count() for u in staff_aseo}
    return min(cargas, key=cargas.get)

def obtener_tecnico_disponible():
    staff_mant = list(User.objects.filter(groups__name='mantenimiento').order_by('id'))
    if not staff_mant:
        return None
    cargas = {u: OrdenMantenimiento.objects.filter(asignado_a=u, estado__in=['Abierta', 'EnReparacion']).count() for u in staff_mant}
    return min(cargas, key=cargas.get)

# ========================================================
# VISTAS PÚBLICAS Y RESERVAS WEB
# ========================================================

def sincronizar_reservas_y_habitaciones_automatico():
    """
    Regla de Negocio Automatizada:
    1. Si una reserva ya superó su fecha de Check-out (checkout < hoy) y estaba Ocupada o CheckIn,
       finaliza la estadía de la reserva a CheckOut y marca la habitación como 'Sucia'
       enviando automáticamente orden de sanitización a Housekeeping.
    2. Si una habitación 'Ocupada' no tiene ninguna reserva activa en el día de hoy,
       se libera a 'Disponible' (o 'Sucia' si requiere aseo).
    """
    hoy = datetime.date.today()
    
    # Reservas vencidas
    reservas_vencidas = Reserva.objects.filter(
        fecha_checkout__lt=hoy,
        estado__in=['Confirmada', 'CheckIn']
    ).select_related('habitacion')

    for r in reservas_vencidas:
        r.estado = 'CheckOut'
        r.save()
        hab = r.habitacion
        if hab.estado == 'Ocupada':
            hab.estado = 'Sucia'
            hab.save()
            t, created = TareaLimpieza.objects.get_or_create(habitacion=hab, estado='Pendiente')
            if created or not t.responsable:
                t.responsable = obtener_camarera_disponible()
                t.save()

def index(request):
    sincronizar_reservas_y_habitaciones_automatico()
    hoy = datetime.date.today()

    tipos = TipoHabitacion.objects.all()
    habitaciones = Habitación.objects.all()
    cliente_nombre = None
    reserva_activa = None
    reserva_futura = None
    folio_huesped = None

    if request.user.is_authenticated:
        c = Cliente.objects.filter(email=request.user.email).first()
        cliente_nombre = c.nombre_completo if c else request.user.first_name or request.user.username
        
        if c:
            # 1. Estadía en Curso: Check-in ya realizado o fecha_checkin <= hoy <= fecha_checkout
            reserva_activa = Reserva.objects.filter(
                cliente=c,
                estado__in=['CheckIn', 'Confirmada'],
                fecha_checkin__lte=hoy,
                fecha_checkout__gte=hoy
            ).order_by('-id').first()

            if reserva_activa and hasattr(reserva_activa, 'folio'):
                folio_huesped = reserva_activa.folio

            # 2. Si no está en curso hoy, verificar si tiene una Reserva Futura Confirmada
            if not reserva_activa:
                reserva_futura = Reserva.objects.filter(
                    cliente=c,
                    estado='Confirmada',
                    fecha_checkin__gt=hoy
                ).order_by('fecha_checkin').first()

    return render(request, 'publico/index.html', {
        'tipos': tipos,
        'habitaciones': habitaciones,
        'cliente_nombre': cliente_nombre,
        'reserva_activa': reserva_activa,
        'reserva_futura': reserva_futura,
        'folio_huesped': folio_huesped,
        'hoy': hoy,
    })

def buscar_disponibilidad_api(request):
    sincronizar_reservas_y_habitaciones_automatico()
    hoy = datetime.date.today()

    checkin_str = request.GET.get('checkin')
    checkout_str = request.GET.get('checkout')

    if not checkin_str or not checkout_str:
        return JsonResponse({'status': 'error', 'message': 'Debes seleccionar fecha de llegada y salida.'}, status=400)

    try:
        f_in = datetime.datetime.strptime(checkin_str, '%Y-%m-%d').date()
        f_out = datetime.datetime.strptime(checkout_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'status': 'error', 'message': 'Formato de fecha inválido (AAAA-MM-DD).'}, status=400)

    # Validaciones temporales estrictas (CU-01 / RN-01)
    if f_in < hoy:
        return JsonResponse({'status': 'error', 'message': f'La fecha de llegada ({f_in.strftime("%d/%m/%Y")}) no puede ser anterior al día de hoy ({hoy.strftime("%d/%m/%Y")}).'}, status=400)

    if f_out <= f_in:
        return JsonResponse({'status': 'error', 'message': f'La fecha de salida ({f_out.strftime("%d/%m/%Y")}) debe ser posterior a la fecha de llegada ({f_in.strftime("%d/%m/%Y")}).'}, status=400)

    # Habitaciones con reservas confirmadas o check-in que se solapan con este rango (RN-01)
    reservas_solapadas = set(Reserva.objects.filter(
        estado__in=['Confirmada', 'CheckIn'],
        fecha_checkin__lt=f_out,
        fecha_checkout__gt=f_in
    ).values_list('habitacion__numero', flat=True))

    # Habitaciones disponibles: No solapadas y aptas
    habitaciones = Habitación.objects.exclude(numero__in=reservas_solapadas).exclude(estado__in=['Mantenimiento', 'Sucia', 'EnLimpieza']).select_related('tipo').order_by('numero')

    data = []
    for h in habitaciones:
        data.append({
            'numero': h.numero,
            'tipo': h.tipo.nombre,
            'precio': int(h.tipo.precio_base),
            'capacidad': h.tipo.capacidad_personas,
            'descripcion': h.tipo.descripcion or '',
            'imagen': h.tipo.imagen_url or ''
        })
    return JsonResponse({'status': 'ok', 'habitaciones': data, 'noches': (f_out - f_in).days})

@require_POST
def cliente_registro_api(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Datos malformados.'}, status=400)

    nombre = data.get('nombre', '').strip()
    email = data.get('email', '').strip().lower()
    telefono = data.get('telefono', '').strip()
    rut = data.get('rut', '').strip()
    password = data.get('password', '')
    password_confirm = data.get('password_confirm', '')

    if not nombre or not email or not password or not password_confirm:
        return JsonResponse({'status': 'error', 'message': 'Todos los campos obligatorios deben ser completados.'}, status=400)

    # Validación estricta de correo real
    correo_valido, msg_correo = validar_correo_real(email)
    if not correo_valido:
        return JsonResponse({'status': 'error', 'message': msg_correo}, status=400)

    # Validación de documento de identidad (RUT o Pasaporte)
    tipo_doc = data.get('tipo_doc', 'rut')
    doc_valido, msg_doc, rut_limpio = validar_documento_identidad(tipo_doc, rut)
    if not doc_valido:
        return JsonResponse({'status': 'error', 'message': msg_doc}, status=400)
    rut = rut_limpio

    # Validación de número telefónico
    tel_valido, msg_tel, tel_formateado = validar_telefono_chileno(telefono)
    if not tel_valido:
        return JsonResponse({'status': 'error', 'message': msg_tel}, status=400)
    telefono = tel_formateado

    # Validación estricta de contraseña según normativa chilena (Ley 21.459 y 21.719)
    errores_clave = validar_politica_contrasena_chile(password, password_confirm)
    if errores_clave:
        return JsonResponse({'status': 'error', 'message': ' | '.join(errores_clave)}, status=400)

    if User.objects.filter(username=email).exists() or Cliente.objects.filter(email=email).exists():
        return JsonResponse({'status': 'error', 'message': 'El correo electrónico ya se encuentra registrado.'}, status=400)

    with transaction.atomic():
        user = User.objects.create_user(username=email, email=email, password=password, first_name=nombre)
        grupo_cliente, _ = Group.objects.get_or_create(name='cliente')
        user.groups.add(grupo_cliente)
        Cliente.objects.create(user=user, nombre_completo=nombre, email=email, telefono=telefono, rut=rut)

    return JsonResponse({'status': 'ok', 'message': '¡Cuenta creada con éxito! Ahora puedes iniciar sesión de forma segura.'})

@require_POST
def cliente_login_api(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Datos malformados.'}, status=400)

    paso = data.get('paso', 'credenciales') # 'credenciales' o 'mfa'
    email = data.get('email', '').strip().lower()

    if paso == 'credenciales':
        password = data.get('password', '')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            # Credenciales primarias válidas -> Generar datos MFA (QR y código OTP)
            mfa_data = generar_datos_mfa(user)
            request.session['mfa_pending_user_id'] = user.id
            cliente = Cliente.objects.filter(email=email).first()
            tel_oculto = ""
            if cliente and cliente.telefono:
                t = cliente.telefono
                tel_oculto = t[:4] + " **** " + t[-4:] if len(t) >= 8 else t

            return JsonResponse({
                'status': 'mfa_required',
                'message': 'Credenciales verificadas. Ingrese el segundo factor de autenticación (MFA).',
                'email': email,
                'telefono_oculto': tel_oculto,
                'qr_b64': mfa_data['qr_b64'],
                'codigo_demo': mfa_data['current_otp'],
                'secret': mfa_data['secret']
            })
        else:
            return JsonResponse({'status': 'error', 'message': 'Correo o contraseña incorrectos. Por favor verifique sus datos.'}, status=400)

    elif paso == 'mfa':
        codigo_otp = data.get('codigo_otp', '').strip()
        user_id = request.session.get('mfa_pending_user_id')
        if not user_id:
            return JsonResponse({'status': 'error', 'message': 'La sesión de autenticación ha expirado. Reintente desde el inicio.'}, status=400)

        user = User.objects.filter(id=user_id).first()
        if not user:
            return JsonResponse({'status': 'error', 'message': 'Usuario no válido.'}, status=400)

        if validar_codigo_mfa(user, codigo_otp):
            login(request, user)
            if 'mfa_pending_user_id' in request.session:
                del request.session['mfa_pending_user_id']
            cliente = Cliente.objects.filter(email=user.email).first()
            nombre = cliente.nombre_completo if cliente else user.first_name or user.username
            return JsonResponse({'status': 'ok', 'nombre': nombre, 'email': user.email, 'message': '¡Autenticación en 2 pasos exitosa!'})
        else:
            return JsonResponse({'status': 'error', 'message': 'Código de seguridad incorrecto o expirado (30s). Intente nuevamente.'}, status=400)

    return JsonResponse({'status': 'error', 'message': 'Paso no reconocido.'}, status=400)

@require_POST
def cliente_logout_api(request):
    logout(request)
    return JsonResponse({'status': 'ok', 'message': 'Sesión cerrada.'})

@require_POST
def reservar_publico_api(request):
    sincronizar_reservas_y_habitaciones_automatico()
    hoy = datetime.date.today()

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Datos malformados.'}, status=400)

    numero_hab = data.get('habitacion_id')
    nombre = data.get('nombre')
    email = data.get('email')
    checkin_str = data.get('checkin')
    checkout_str = data.get('checkout')

    if not checkin_str or not checkout_str:
        return JsonResponse({'status': 'error', 'message': 'Debes especificar las fechas de llegada y salida para reservar.'}, status=400)

    try:
        f_in = datetime.datetime.strptime(checkin_str, '%Y-%m-%d').date()
        f_out = datetime.datetime.strptime(checkout_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'status': 'error', 'message': 'Formato de fecha inválido.'}, status=400)

    if f_in < hoy:
        return JsonResponse({'status': 'error', 'message': f'La fecha de llegada ({f_in.strftime("%d/%m/%Y")}) no puede ser anterior a hoy ({hoy.strftime("%d/%m/%Y")}).'}, status=400)

    if f_out <= f_in:
        return JsonResponse({'status': 'error', 'message': 'La fecha de salida debe ser posterior a la de llegada.'}, status=400)

    if request.user.is_authenticated:
        c = Cliente.objects.filter(email=request.user.email).first()
        if c:
            nombre = c.nombre_completo
            email = c.email
        else:
            nombre = request.user.first_name or request.user.username
            email = request.user.email

    if not nombre or not email:
        return JsonResponse({'status': 'error', 'message': 'Debes iniciar sesión con tu cuenta de huésped para reservar.'}, status=400)

    hab = get_object_or_404(Habitación, numero=numero_hab)

    # Validar que no haya cruce de reservas en ese rango
    solapada = Reserva.objects.filter(
        habitacion=hab,
        estado__in=['Confirmada', 'CheckIn'],
        fecha_checkin__lt=f_out,
        fecha_checkout__gt=f_in
    ).exists()

    if solapada or hab.estado in ['Mantenimiento', 'Sucia', 'EnLimpieza']:
        return JsonResponse({'status': 'error', 'message': f'La habitación #{numero_hab} no está disponible para las fechas seleccionadas.'}, status=400)

    noches = max(1, (f_out - f_in).days)
    monto_total = hab.tipo.precio_base * noches

    with transaction.atomic():
        cliente, _ = Cliente.objects.get_or_create(
            email=email,
            defaults={'nombre_completo': nombre}
        )
        codigo = f"RES-{hab.numero}-{int(timezone.now().timestamp()) % 10000}"
        
        # Si la reserva comienza hoy mismo, pasa a CheckIn y ocupa la habitación; si es a futuro, queda Confirmada
        es_hoy = (f_in == hoy)
        estado_reserva = 'CheckIn' if es_hoy else 'Confirmada'

        reserva = Reserva.objects.create(
            codigo_reserva=codigo,
            cliente=cliente,
            habitacion=hab,
            fecha_checkin=f_in,
            fecha_checkout=f_out,
            num_huespedes=hab.tipo.capacidad_personas,
            estado=estado_reserva
        )
        folio = Folio.objects.create(reserva=reserva)
        Cargo.objects.create(
            folio=folio,
            descripcion=f"Alojamiento {hab.tipo.nombre} ({noches} noche{'s' if noches > 1 else ''}: {f_in.strftime('%d/%m')} al {f_out.strftime('%d/%m')})",
            monto=monto_total
        )
        
        if es_hoy:
            hab.estado = 'Ocupada'
            hab.save()

    msg_extra = "¡Tu estadía comienza hoy! Puedes acceder a los servicios de habitación." if es_hoy else f"Tu reserva futura quedó confirmada para el {f_in.strftime('%d/%m/%Y')}."
    return JsonResponse({'status': 'ok', 'message': f'¡Reserva {codigo} creada con éxito! {msg_extra}'})

@login_required
@require_POST
def huesped_solicitar_servicio(request):
    c = Cliente.objects.filter(email=request.user.email).first()
    if not c:
        return JsonResponse({'status': 'error', 'message': 'Perfil de huésped no encontrado.'}, status=400)

    reserva = Reserva.objects.filter(cliente=c).exclude(estado='CheckOut').order_by('-id').first()
    if not reserva or not hasattr(reserva, 'folio'):
        return JsonResponse({'status': 'error', 'message': 'No tienes una estadía activa para cargar servicios.'}, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Datos inválidos.'}, status=400)

    tipo_solicitud = data.get('tipo', 'consumo') # 'consumo', 'aseo', 'mantenimiento'
    detalle = data.get('detalle', '').strip()
    monto = int(data.get('monto', 0))

    with transaction.atomic():
        if tipo_solicitud == 'aseo':
            # Solicitud de insumos/limpieza a Housekeeping durante la estadía
            tarea = TareaLimpieza.objects.create(
                habitacion=reserva.habitacion,
                estado='Pendiente',
                observaciones=f"[Solicitud Huésped - Hab {reserva.habitacion.numero}] {detalle}"
            )
            return JsonResponse({'status': 'ok', 'message': f'Solicitud enviada a Housekeeping: "{detalle}". El personal acudirá a tu habitación a la brevedad.'})

        elif tipo_solicitud == 'mantenimiento':
            # Reporte de falla técnica en habitación ocupada
            OrdenMantenimiento.objects.create(
                habitacion=reserva.habitacion,
                descripcion_falla=f"[Reporte Huésped - Hab {reserva.habitacion.numero}] {detalle}",
                estado='Abierta',
                reportado_por=request.user
            )
            return JsonResponse({'status': 'ok', 'message': f'Falla técnica reportada: "{detalle}". El equipo de Mantenimiento fue notificado.'})

        else:
            # Consumo con cargo al folio (Room Service, Spa, Minibar)
            servicio = data.get('servicio', 'Servicio a la Habitación')
            if monto <= 0:
                monto = 15000
            Cargo.objects.create(folio=reserva.folio, descripcion=f"Solicitud Web: {servicio}", monto=monto)
            return JsonResponse({'status': 'ok', 'message': f'¡{servicio} solicitado y cargado a tu folio de habitación!'})

@login_required
@require_POST
def huesped_abono_online(request):
    c = Cliente.objects.filter(email=request.user.email).first()
    if not c:
        return JsonResponse({'status': 'error', 'message': 'Perfil de huésped no encontrado.'}, status=400)

    reserva = Reserva.objects.filter(cliente=c).exclude(estado='CheckOut').order_by('-id').first()
    if not reserva or not hasattr(reserva, 'folio'):
        return JsonResponse({'status': 'error', 'message': 'No tienes una reserva activa con folio abierto.'}, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Datos inválidos.'}, status=400)

    monto = int(data.get('monto', 0))
    if monto <= 0:
        return JsonResponse({'status': 'error', 'message': 'Monto de pago inválido.'}, status=400)

    ts = int(timezone.now().timestamp()) % 100000
    buy_order = f"SUAH-{reserva.folio.id}-{ts}"
    session_id = f"SESS-{request.user.id}-{ts}"
    return_url = request.build_absolute_uri('/webpay/retorno/')

    try:
        wp_res = iniciar_pago_webpay(buy_order, session_id, monto, return_url)
        # Guardar datos en sesión para verificar tras el retorno
        request.session['webpay_pending'] = {
            'folio_id': reserva.folio.id,
            'monto': monto,
            'buy_order': buy_order,
            'token': wp_res['token']
        }
        return JsonResponse({
            'status': 'ok',
            'action': 'redirect_webpay',
            'url': wp_res['url'],
            'token_ws': wp_res['token']
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': f'Error al conectar con Transbank Webpay Developers: {str(e)}'}, status=500)

def webpay_retorno_view(request):
    token_ws = request.POST.get('token_ws') or request.GET.get('token_ws')
    tbk_token = request.POST.get('TBK_TOKEN') or request.GET.get('TBK_TOKEN')

    # Transacción anulada por el usuario en Transbank
    if tbk_token and not token_ws:
        return render(request, 'publico/webpay_resultado.html', {
            'exito': False,
            'buy_order': request.POST.get('TBK_ORDEN_COMPRA', 'N/A'),
            'monto': 0,
            'mensaje_error': 'La transacción fue anulada por el usuario en el portal de Transbank.'
        })

    if not token_ws:
        return render(request, 'publico/webpay_resultado.html', {
            'exito': False,
            'monto': 0,
            'mensaje_error': 'No se recibió el token de confirmación de Transbank.'
        })

    try:
        commit_res = confirmar_pago_webpay(token_ws)
        status = commit_res.get('status')
        response_code = commit_res.get('response_code')
        amount = commit_res.get('amount', 0)
        buy_order = commit_res.get('buy_order', 'N/A')
        auth_code = commit_res.get('authorization_code', 'N/A')
        card_detail = commit_res.get('card_detail', {})
        last_digits = card_detail.get('card_number', '****')

        # status == 'AUTHORIZED' y response_code == 0 indica pago aprobado
        if status == 'AUTHORIZED' and response_code == 0:
            pending = request.session.get('webpay_pending', {})
            folio_id = pending.get('folio_id')
            if folio_id:
                folio = Folio.objects.filter(id=folio_id).first()
                if folio:
                    with transaction.atomic():
                        Abono.objects.create(
                            folio=folio,
                            descripcion=f'Pago Online Transbank Webpay Plus (Aut: {auth_code})',
                            monto=amount,
                            metodo_pago='Webpay Plus Developers'
                        )
            if 'webpay_pending' in request.session:
                del request.session['webpay_pending']

            return render(request, 'publico/webpay_resultado.html', {
                'exito': True,
                'monto': f"{int(amount):,}",
                'buy_order': buy_order,
                'auth_code': auth_code,
                'last_digits': last_digits,
                'payment_type': 'Tarjeta Débito / Crédito (Webpay Plus)',
                'fecha': timezone.now().strftime('%d-%m-%Y %H:%M:%S')
            })
        else:
            return render(request, 'publico/webpay_resultado.html', {
                'exito': False,
                'monto': f"{int(amount):,}",
                'buy_order': buy_order,
                'mensaje_error': f'Transbank rechazó el pago (Código: {response_code}). Verifique los datos de la tarjeta de prueba.'
            })
    except Exception as e:
        return render(request, 'publico/webpay_resultado.html', {
            'exito': False,
            'monto': 0,
            'mensaje_error': f'Error de comunicación con Transbank: {str(e)}'
        })

# ========================================================
# AUTENTICACIÓN ADMIN / STAFF (RNF-04)
# ========================================================

def login_admin_view(request):
    if request.user.is_authenticated and (request.user.groups.filter(name__in=['recepcion', 'housekeeping', 'mantenimiento']).exists() or request.user.is_superuser):
        return redirect('panel_operativo')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            # Validar que pertenezca a staff o admin
            if not (user.is_superuser or user.groups.filter(name__in=['recepcion', 'housekeeping', 'mantenimiento']).exists()):
                return render(request, 'admin/login.html', {'error': 'Acceso denegado: cuenta no pertenece al personal del hotel.'})

            login(request, user)
            return redirect('panel_operativo')
        else:
            return render(request, 'admin/login.html', {'error': 'Credenciales incorrectas o usuario no autorizado.'})

    return render(request, 'admin/login.html')

def logout_admin_view(request):
    logout(request)
    return redirect('login_admin')

@login_required
def panel_operativo(request):
    sincronizar_reservas_y_habitaciones_automatico()
    rol = obtener_rol_usuario(request.user)
    habitaciones = Habitación.objects.all().select_related('tipo').order_by('numero')

    total = habitaciones.count()
    disponibles = habitaciones.filter(estado='Disponible').count()
    ocupadas = habitaciones.filter(estado='Ocupada').count()
    sucias = habitaciones.filter(estado='Sucia').count()
    en_limpieza = habitaciones.filter(estado='EnLimpieza').count()
    mantenimiento = habitaciones.filter(estado='Mantenimiento').count()
    ocupacion_pct = int((ocupadas / total * 100)) if total > 0 else 0

    # Solicitudes de Huéspedes en habitaciones ocupadas
    solicitudes_aseo_ocupadas = TareaLimpieza.objects.filter(
        habitacion__estado='Ocupada',
        estado__in=['Pendiente', 'EnProceso']
    ).select_related('habitacion').order_by('-id')

    tickets_mantenimiento = OrdenMantenimiento.objects.filter(
        estado__in=['Abierta', 'EnReparacion']
    ).select_related('habitacion', 'reportado_por').order_by('-id')

    # Mensajes de Contacto web recibidos (para Recepción y Administrador)
    mensajes_contacto = MensajeContacto.objects.all().select_related('respondido_por').order_by('-fecha_envio')
    mensajes_pendientes_count = mensajes_contacto.filter(estado='Pendiente').count()

    # Personal de staff para asignaciones y nómina general
    staff_aseo = User.objects.filter(groups__name='housekeeping').order_by('first_name')
    staff_mant = User.objects.filter(groups__name='mantenimiento').order_by('first_name')
    nomina_personal = User.objects.filter(
        groups__name__in=['recepcion', 'housekeeping', 'mantenimiento']
    ).distinct().order_by('first_name')

    # Historial de Limpiezas finalizadas
    historial_limpiezas = TareaLimpieza.objects.filter(
        estado='Finalizada'
    ).select_related('habitacion', 'responsable').order_by('-fecha_actualizacion')[:40]

    # Historial de Mantenimientos resueltos
    historial_mantenimientos = OrdenMantenimiento.objects.filter(
        estado='Resuelta'
    ).select_related('habitacion', 'reportado_por', 'asignado_a').order_by('-fecha_resolucion')[:40]

    dict_tareas = {t.habitacion.numero: t for t in TareaLimpieza.objects.filter(estado__in=['Pendiente', 'EnProceso']).select_related('responsable')}
    habitaciones_json_data = []
    for h in habitaciones:
        t = dict_tareas.get(h.numero)
        habitaciones_json_data.append({
            'id': h.numero,
            'type': h.tipo.nombre,
            'price': int(h.tipo.precio_base),
            'status': h.estado,
            'ticket': h.ticket_falla or None,
            'tarea_id': t.id if t else None,
            'responsable_id': t.responsable.id if (t and t.responsable) else None,
            'responsable_nombre': (t.responsable.get_full_name() or t.responsable.username) if (t and t.responsable) else 'Sin Asignar',
        })

    return render(request, 'admin/panel.html', {
        'rol': rol,
        'habitaciones': habitaciones,
        'habitaciones_json': json.dumps(habitaciones_json_data),
        'total': total,
        'disponibles': disponibles,
        'ocupadas': ocupadas,
        'sucias': sucias,
        'en_limpieza': en_limpieza,
        'mantenimiento': mantenimiento,
        'ocupacion_pct': ocupacion_pct,
        'solicitudes_aseo_ocupadas': solicitudes_aseo_ocupadas,
        'tickets_mantenimiento': tickets_mantenimiento,
        'mensajes_contacto': mensajes_contacto,
        'mensajes_pendientes_count': mensajes_pendientes_count,
        'staff_aseo': staff_aseo,
        'staff_mant': staff_mant,
        'nomina_personal': nomina_personal,
        'historial_limpiezas': historial_limpiezas,
        'historial_mantenimientos': historial_mantenimientos,
    })

@login_required
def get_room_folio(request, numero):
    if not es_recepcionista(request.user):
        return HttpResponseForbidden("Acceso denegado: solo personal de Recepción puede ver folios.")

    hab = get_object_or_404(Habitación, numero=numero)
    reserva_activa = hab.reservas.filter(estado__in=['Confirmada', 'CheckIn']).last()
    
    folio_data = None
    if reserva_activa and hasattr(reserva_activa, 'folio'):
        f = reserva_activa.folio
        dias = max(1, (reserva_activa.fecha_checkout - reserva_activa.fecha_checkin).days)
        folio_data = {
            'codigo_reserva': reserva_activa.codigo_reserva,
            'guest': reserva_activa.cliente.nombre_completo,
            'email': reserva_activa.cliente.email,
            'rut': reserva_activa.cliente.rut or 'No informado',
            'telefono': reserva_activa.cliente.telefono or 'No informado',
            'checkin': reserva_activa.fecha_checkin.strftime('%d/%m/%Y'),
            'checkout': reserva_activa.fecha_checkout.strftime('%d/%m/%Y'),
            'noches': dias,
            'cargos': [{'desc': c.descripcion, 'amount': int(c.monto)} for c in f.cargos.all()],
            'payments': [{'desc': a.descripcion, 'amount': int(a.monto)} for a in f.abonos.all()],
            'total_charges': int(f.total_cargos),
            'total_payments': int(f.total_abonos),
            'balance': int(f.saldo_pendiente)
        }

    return JsonResponse({
        'numero': hab.numero,
        'tipo': hab.tipo.nombre,
        'precio': int(hab.tipo.precio_base),
        'estado': hab.estado,
        'ticket': hab.ticket_falla,
        'folio': folio_data
    })

@login_required
@require_POST
def agregar_consumo(request, numero):
    if not es_recepcionista(request.user):
        return HttpResponseForbidden("Acceso denegado.")

    hab = get_object_or_404(Habitación, numero=numero)
    reserva = hab.reservas.filter(estado__in=['Confirmada', 'CheckIn']).last()
    if not reserva or not hasattr(reserva, 'folio'):
        return JsonResponse({'status': 'error', 'message': 'No hay reserva o folio activo.'}, status=400)

    data = json.loads(request.body)
    desc = data.get('desc', 'Consumo Extra')
    monto = int(data.get('amount', 15000))

    Cargo.objects.create(folio=reserva.folio, descripcion=desc, monto=monto)
    return JsonResponse({'status': 'ok', 'message': 'Consumo añadido con éxito.'})

@login_required
@require_POST
def abonar_folio(request, numero):
    if not es_recepcionista(request.user):
        return HttpResponseForbidden("Acceso denegado.")

    hab = get_object_or_404(Habitación, numero=numero)
    reserva = hab.reservas.filter(estado__in=['Confirmada', 'CheckIn']).last()
    if not reserva or not hasattr(reserva, 'folio'):
        return JsonResponse({'status': 'error', 'message': 'No hay folio activo.'}, status=400)

    data = json.loads(request.body)
    monto = int(data.get('monto', 0))
    if monto <= 0:
        return JsonResponse({'status': 'error', 'message': 'El monto a abonar debe ser mayor a cero.'}, status=400)

    Abono.objects.create(folio=reserva.folio, descripcion='Abono en Caja', monto=monto)
    return JsonResponse({'status': 'ok', 'message': 'Abono registrado con éxito.'})

@login_required
@require_POST
def checkin_manual(request, numero):
    """
    Check-in directo desde mostrador (Recepción) con registro real del huésped.
    """
    if not es_recepcionista(request.user):
        return HttpResponseForbidden("Acceso denegado: solo personal de Recepción.")

    hab = get_object_or_404(Habitación, numero=numero)
    if hab.estado != 'Disponible':
        return JsonResponse({'status': 'error', 'message': 'La habitación no está disponible.'}, status=400)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Datos malformados.'}, status=400)

    nombre = data.get('nombre', '').strip()
    rut = data.get('rut', '').strip()
    email = data.get('email', '').strip().lower()
    telefono = data.get('telefono', '').strip()
    noches = int(data.get('noches', 1))

    if not nombre or not email:
        return JsonResponse({'status': 'error', 'message': 'El nombre y el correo del huésped son obligatorios.'}, status=400)

    # Validación de correo real
    correo_valido, msg_correo = validar_correo_real(email)
    if not correo_valido:
        return JsonResponse({'status': 'error', 'message': msg_correo}, status=400)

    # Validación de documento (RUT / Pasaporte)
    tipo_doc = data.get('tipo_doc', 'rut')
    doc_valido, msg_doc, rut_limpio = validar_documento_identidad(tipo_doc, rut)
    if not doc_valido:
        return JsonResponse({'status': 'error', 'message': msg_doc}, status=400)
    rut = rut_limpio

    # Validación de número telefónico
    tel_valido, msg_tel, tel_formateado = validar_telefono_chileno(telefono)
    if not tel_valido:
        return JsonResponse({'status': 'error', 'message': msg_tel}, status=400)
    telefono = tel_formateado

    with transaction.atomic():
        # Registrar o actualizar la ficha del huésped
        cliente, _ = Cliente.objects.get_or_create(
            email=email,
            defaults={'nombre_completo': nombre, 'rut': rut, 'telefono': telefono}
        )
        if rut and not cliente.rut:
            cliente.rut = rut
        if telefono and not cliente.telefono:
            cliente.telefono = telefono
        if nombre:
            cliente.nombre_completo = nombre
        cliente.save()

        # Calcular fechas de estadía
        hoy = datetime.date.today()
        salida = hoy + datetime.timedelta(days=max(1, noches))

        codigo = f"RES-{hab.numero}-{int(timezone.now().timestamp()) % 10000}"
        reserva = Reserva.objects.create(
            codigo_reserva=codigo,
            cliente=cliente,
            habitacion=hab,
            fecha_checkin=hoy,
            fecha_checkout=salida,
            num_huespedes=hab.tipo.capacidad_personas,
            estado='CheckIn'
        )

        # Crear folio y cargar noches de alojamiento
        folio = Folio.objects.create(reserva=reserva)
        monto_alojamiento = hab.tipo.precio_base * noches
        Cargo.objects.create(
            folio=folio,
            descripcion=f"Alojamiento ({noches} noche{'s' if noches > 1 else ''}) - Tarifa Mostrador",
            monto=monto_alojamiento
        )

        # Si el recepcionista registró un abono inicial en el checkin
        abono_inicial = int(data.get('abono_inicial', 0))
        if abono_inicial > 0:
            metodo = data.get('metodo_abono', 'Efectivo en Caja')
            Abono.objects.create(
                folio=folio,
                descripcion='Abono Inicial Check-in',
                monto=abono_inicial,
                metodo_pago=metodo
            )

        # Cambiar estado de la habitación
        hab.estado = 'Ocupada'
        hab.save()

    return JsonResponse({'status': 'ok', 'message': f'¡Check-in realizado con éxito para {nombre}! Habitación #{hab.numero} ocupada.'})

def finalizar_checkout(request, numero):
    if not es_recepcionista(request.user):
        return HttpResponseForbidden("Acceso denegado.")

    hab = get_object_or_404(Habitación, numero=numero)
    reserva = hab.reservas.filter(estado__in=['Confirmada', 'CheckIn']).last()
    
    with transaction.atomic():
        if reserva and hasattr(reserva, 'folio'):
            if reserva.folio.saldo_pendiente > 0:
                return JsonResponse({'status': 'error', 'message': f'Saldo pendiente de ${int(reserva.folio.saldo_pendiente):,} CLP. Debe liquidar antes del check-out.'}, status=400)
            reserva.estado = 'CheckOut'
            reserva.folio.abierto = False
            reserva.folio.fecha_cierre = timezone.now()
            reserva.folio.save()
            reserva.save()

        hab.estado = 'Sucia'
        hab.save()
        TareaLimpieza.objects.create(habitacion=hab, estado='Pendiente', responsable=obtener_camarera_disponible())

    return JsonResponse({'status': 'ok', 'message': 'Check-out listo. Habitación enviada a Housekeeping (SUCIA).'})

@login_required
@require_POST
def reportar_falla(request, numero):
    hab = get_object_or_404(Habitación, numero=numero)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = {}
    desc = data.get('descripcion', 'Falla técnica no especificada')
    mantener_ocupada = (hab.estado == 'Ocupada')

    with transaction.atomic():
        if not mantener_ocupada:
            hab.estado = 'Mantenimiento'
            hab.ticket_falla = desc
            hab.save()

        prefijo = "[Habitación Ocupada] " if mantener_ocupada else ""
        tecnico_auto = obtener_tecnico_disponible()
        OrdenMantenimiento.objects.create(
            habitacion=hab,
            descripcion_falla=f"{prefijo}{desc}",
            reportado_por=request.user,
            asignado_a=tecnico_auto
        )

    if mantener_ocupada:
        return JsonResponse({'status': 'ok', 'message': f'Ticket de falla reportado a Mantenimiento para la Habitación {numero} (manteniendo huésped alojado).'})
    return JsonResponse({'status': 'ok', 'message': f'Falla registrada y habitación {numero} bloqueada preventivamente.'})


@login_required
@require_POST
def recepcion_solicitar_aseo_ocupada(request, numero):
    hab = get_object_or_404(Habitación, numero=numero)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = {}
    detalle = data.get('detalle', 'Insumos / Aseo solicitado en mostrador').strip()

    with transaction.atomic():
        TareaLimpieza.objects.create(
            habitacion=hab,
            estado='Pendiente',
            observaciones=f"[Recepción - Hab {numero}] {detalle}"
        )

    return JsonResponse({'status': 'ok', 'message': f'Solicitud de aseo/insumos enviada a Housekeeping para la Habitación {numero}.'})


@login_required
@require_POST
def atender_solicitud_aseo_ocupada(request, tarea_id):
    if not es_housekeeping(request.user):
        return HttpResponseForbidden("Acceso denegado: solo personal de Housekeeping.")

    tarea = get_object_or_404(TareaLimpieza, id=tarea_id)
    tarea.estado = 'Finalizada'
    tarea.responsable = request.user
    tarea.save()

    return JsonResponse({'status': 'ok', 'message': f'Solicitud #{tarea_id} de insumos/aseo completada con éxito.'})

@login_required
@require_POST
def cambiar_estado_aseo(request, numero):
    if not es_housekeeping(request.user):
        return HttpResponseForbidden("Acceso denegado: solo personal de Housekeeping.")

    hab = get_object_or_404(Habitación, numero=numero)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Datos malformados.'}, status=400)

    accion = data.get('accion')

    with transaction.atomic():
        if accion == 'iniciar':
            hab.estado = 'EnLimpieza'
            hab.save()
            tarea = TareaLimpieza.objects.filter(habitacion=hab, estado__in=['Pendiente', 'EnProceso']).order_by('-id').first()
            if not tarea:
                tarea = TareaLimpieza.objects.create(habitacion=hab, estado='EnProceso', responsable=request.user)
            else:
                tarea.estado = 'EnProceso'
                tarea.responsable = request.user
                tarea.save()
            return JsonResponse({'status': 'ok', 'message': f'Aseo iniciado en habitación {numero}.', 'estado': hab.estado})

        elif accion == 'finalizar':
            checklist = data.get('checklist', {})
            observaciones = data.get('observaciones', '').strip()

            hab.estado = 'Disponible'
            hab.save()

            tarea = TareaLimpieza.objects.filter(habitacion=hab, estado__in=['EnProceso', 'Pendiente']).last()
            if not tarea:
                tarea = TareaLimpieza.objects.create(habitacion=hab, responsable=request.user)

            tarea.estado = 'Finalizada'
            tarea.responsable = request.user
            tarea.sabanas_cambiadas = bool(checklist.get('sabanas', True))
            tarea.toallas_repuestas = bool(checklist.get('toallas', True))
            tarea.bano_desinfectado = bool(checklist.get('bano', True))
            tarea.amenities_completos = bool(checklist.get('amenities', True))
            tarea.piso_aspirado = bool(checklist.get('piso', True))
            if observaciones:
                tarea.observaciones = observaciones
            tarea.save()

            return JsonResponse({'status': 'ok', 'message': f'Limpieza e insumos completados. Habitación {numero} marcada como DISPONIBLE.', 'estado': hab.estado})

        elif accion == 'reportar_desperfecto':
            falla = data.get('falla', 'Desperfecto detectado por personal de aseo')
            hab.estado = 'Mantenimiento'
            hab.ticket_falla = falla
            hab.save()

            OrdenMantenimiento.objects.create(
                habitacion=hab,
                descripcion_falla=falla,
                reportado_por=request.user
            )

            tarea = TareaLimpieza.objects.filter(habitacion=hab, estado='EnProceso').first()
            if tarea:
                tarea.observaciones = f"Aseo suspendido por desperfecto: {falla}"
                tarea.save()

            return JsonResponse({'status': 'ok', 'message': f'Desperfecto reportado. Habitación {numero} bloqueada y transferida a Mantenimiento.', 'estado': hab.estado})

    return JsonResponse({'status': 'error', 'message': 'Acción no válida.'}, status=400)

@login_required
@require_POST
def resolver_mantenimiento(request, numero):
    if not es_mantenimiento(request.user):
        return HttpResponseForbidden("Acceso denegado: solo personal de Mantenimiento.")

    hab = get_object_or_404(Habitación, numero=numero)
    with transaction.atomic():
        orden = OrdenMantenimiento.objects.filter(habitacion=hab, estado__in=['Abierta', 'EnReparacion']).last()
        if orden:
            orden.estado = 'Resuelta'
            orden.fecha_resolucion = timezone.now()
            if not orden.asignado_a:
                orden.asignado_a = request.user
            orden.save()

        # Si la habitación estaba Ocupada por un huésped, se mantiene Ocupada
        if hab.estado == 'Ocupada':
            return JsonResponse({'status': 'ok', 'message': f'Falla resuelta con éxito en Habitación {numero} (el huésped continúa alojado).'})

        hab.estado = 'Sucia'
        hab.ticket_falla = None
        hab.save()
        TareaLimpieza.objects.create(habitacion=hab, estado='Pendiente', responsable=obtener_camarera_disponible())

    return JsonResponse({'status': 'ok', 'message': 'Falla resuelta. Habitación derivada a Limpieza para sanitización.'})

@require_POST
def enviar_mensaje_contacto_api(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Datos malformados.'}, status=400)

    nombre = data.get('nombre', '').strip()
    email = data.get('email', '').strip().lower()
    mensaje = data.get('mensaje', '').strip()

    if not nombre or not email or not mensaje:
        return JsonResponse({'status': 'error', 'message': 'Por favor completa todos los campos del formulario.'}, status=400)

    # Validación de correo real (igual que en registro y check-in)
    correo_valido, msg_correo = validar_correo_real(email)
    if not correo_valido:
        return JsonResponse({'status': 'error', 'message': msg_correo}, status=400)

    # Validar límite de caracteres (máximo 300 caracteres)
    if len(mensaje) > 300:
        return JsonResponse({'status': 'error', 'message': 'El mensaje no debe superar los 300 caracteres.'}, status=400)

    if len(mensaje) < 10:
        return JsonResponse({'status': 'error', 'message': 'Por favor escribe un mensaje de al menos 10 caracteres.'}, status=400)

    with transaction.atomic():
        MensajeContacto.objects.create(
            nombre=nombre,
            email=email,
            mensaje=mensaje,
            estado='Pendiente'
        )

    return JsonResponse({
        'status': 'ok',
        'message': f'¡Gracias {nombre}! Tu mensaje ha sido recibido por nuestro equipo de Recepción y Administración.'
    })


@login_required
@require_POST
def responder_mensaje_contacto_api(request, mensaje_id):
    if not (es_recepcionista(request.user) or request.user.is_superuser):
        return HttpResponseForbidden("Solo Recepción y Administración pueden responder mensajes de contacto.")

    msg = get_object_or_404(MensajeContacto, id=mensaje_id)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = {}

    respuesta = data.get('respuesta', '').strip()
    if not respuesta:
        return JsonResponse({'status': 'error', 'message': 'Por favor ingresa el texto de respuesta.'}, status=400)

    with transaction.atomic():
        msg.respuesta = respuesta
        msg.estado = 'Respondido'
        msg.respondido_por = request.user
        msg.fecha_respuesta = timezone.now()
        msg.save()

    return JsonResponse({
        'status': 'ok',
        'message': f'Respuesta registrada y enviada con éxito al correo {msg.email}.'
    })

@login_required
def consultar_disponibilidad_recepcion_api(request):
    """
    CU-01: Consulta disponibilidad e inventario en tiempo real con filtro por fecha.
    Aplica RN-01 (sin superposición de fechas), RN-02 (limpiezas pendientes), RN-03 (bloqueos por mantenimiento).
    """
    if not (es_recepcionista(request.user) or request.user.is_superuser):
        return HttpResponseForbidden("Acceso denegado: solo personal de Recepción.")

    desde_str = request.GET.get('desde')
    hasta_str = request.GET.get('hasta')

    habitaciones = Habitación.objects.all().select_related('tipo').order_by('numero')
    
    # Si no ingresó fechas, retorna el estado actual en vivo
    if not desde_str or not hasta_str:
        data = []
        for h in habitaciones:
            data.append({
                'id': h.numero,
                'type': h.tipo.nombre,
                'price': int(h.tipo.precio_base),
                'status': h.estado,
                'ticket': h.ticket_falla or None,
                'disponible_rango': h.estado == 'Disponible'
            })
        return JsonResponse({'status': 'ok', 'modo': 'en_vivo', 'habitaciones': data})

    try:
        f_desde = datetime.datetime.strptime(desde_str, '%Y-%m-%d').date()
        f_hasta = datetime.datetime.strptime(hasta_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'status': 'error', 'message': 'Formato de fecha inválido (AAAA-MM-DD).'}, status=400)

    hoy = datetime.date.today()
    if f_desde < hoy:
        return JsonResponse({'status': 'error', 'message': f'La fecha de entrada no puede ser anterior al día de hoy ({hoy.strftime("%d/%m/%Y")}).'}, status=400)

    if f_hasta <= f_desde:
        return JsonResponse({'status': 'error', 'message': 'La fecha de salida debe ser posterior a la de entrada.'}, status=400)

    # RN-01: Buscar habitaciones con reservas cruzadas activas en ese rango
    reservas_solapadas = set(Reserva.objects.filter(
        estado__in=['Confirmada', 'CheckIn'],
        fecha_checkin__lt=f_hasta,
        fecha_checkout__gt=f_desde
    ).values_list('habitacion__numero', flat=True))

    data = []
    for h in habitaciones:
        tiene_reserva_cruzada = h.numero in reservas_solapadas
        
        # RN-01 (Sin cruce de reserva), RN-02 (No debe estar sucia ni en limpieza) y RN-03 (No debe estar en mantenimiento ni ocupada)
        # Para que una habitación sea apta y disponible en el rango:
        # 1. No debe tener reserva que se cruce en ese rango (RN-01)
        # 2. Su estado físico actual debe ser 'Disponible' (RN-02 y RN-03)
        es_realmente_disponible = (not tiene_reserva_cruzada) and (h.estado == 'Disponible')

        data.append({
            'id': h.numero,
            'type': h.tipo.nombre,
            'price': int(h.tipo.precio_base),
            'status': h.estado,
            'ticket': h.ticket_falla or None,
            'disponible_rango': es_realmente_disponible,
            'motivo_bloqueo': 'Reserva cruzada (RN-01)' if tiene_reserva_cruzada else (f'Estado actual: {h.estado} (RN-02/RN-03)' if h.estado != 'Disponible' else None)
        })

    return JsonResponse({
        'status': 'ok',
        'modo': 'filtro_fechas',
        'desde': desde_str,
        'hasta': hasta_str,
        'habitaciones': data
    })

@login_required
@require_POST
def asignar_tarea_aseo(request, tarea_id):
    if not (es_housekeeping(request.user) or es_recepcionista(request.user) or request.user.is_superuser):
        return HttpResponseForbidden("No tienes permiso para asignar tareas de aseo.")

    tarea = get_object_or_404(TareaLimpieza, id=tarea_id)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = {}

    user_id = data.get('usuario_id')
    if user_id:
        usuario = get_object_or_404(User, id=user_id)
        tarea.responsable = usuario
        nombre_resp = usuario.get_full_name() or usuario.username
    else:
        tarea.responsable = None
        nombre_resp = "Sin asignar"
    tarea.save()

    return JsonResponse({'status': 'ok', 'message': f'Tarea asignada exitosamente a {nombre_resp}.'})


@login_required
@require_POST
def asignar_orden_mantenimiento(request, orden_id):
    if not (es_mantenimiento(request.user) or es_recepcionista(request.user) or request.user.is_superuser):
        return HttpResponseForbidden("No tienes permiso para asignar órdenes de mantenimiento.")

    orden = get_object_or_404(OrdenMantenimiento, id=orden_id)
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        data = {}

    user_id = data.get('usuario_id')
    if user_id:
        usuario = get_object_or_404(User, id=user_id)
        orden.asignado_a = usuario
        nombre_resp = usuario.get_full_name() or usuario.username
    else:
        orden.asignado_a = None
        nombre_resp = "Sin asignar"
    orden.save()

    return JsonResponse({'status': 'ok', 'message': f'Orden asignada exitosamente al técnico {nombre_resp}.'})

@login_required
@require_POST
def crear_personal_api(request):
    if not (request.user.is_superuser or request.user.groups.filter(name='admin').exists()):
        return HttpResponseForbidden("Solo el Administrador General puede dar de alta nuevo personal.")

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Datos inválidos.'}, status=400)

    nombre = data.get('nombre', '').strip()
    apellido = data.get('apellido', '').strip()
    email = data.get('email', '').strip().lower()
    rol = data.get('rol', '').strip()
    password = data.get('password', '').strip()

    if not nombre or not apellido or not email or not rol or not password:
        return JsonResponse({'status': 'error', 'message': 'Todos los campos son obligatorios.'}, status=400)

    if rol not in ['recepcion', 'housekeeping', 'mantenimiento']:
        return JsonResponse({'status': 'error', 'message': 'El rol seleccionado no es válido.'}, status=400)

    if User.objects.filter(username=email).exists():
        return JsonResponse({'status': 'error', 'message': f'Ya existe un usuario registrado con el correo {email}.'}, status=400)

    if len(password) < 4:
        return JsonResponse({'status': 'error', 'message': 'La contraseña inicial debe tener al menos 4 caracteres.'}, status=400)

    with transaction.atomic():
        nuevo_user = User.objects.create_user(
            username=email,
            email=email,
            password=password,
            first_name=nombre,
            last_name=apellido
        )
        grupo = Group.objects.filter(name=rol).first()
        if grupo:
            nuevo_user.groups.add(grupo)

    return JsonResponse({
        'status': 'ok',
        'message': f'Empleado/a {nombre} {apellido} registrado/a exitosamente en el área de {rol.capitalize()}.'
    })
