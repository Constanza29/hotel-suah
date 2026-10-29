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
from operaciones.models import TareaLimpieza, OrdenMantenimiento
from core.security_validators import validar_politica_contrasena_chile
from core.rut_and_email_validators import validar_documento_identidad, validar_correo_real, validar_telefono_chileno

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

# ========================================================
# VISTAS PÚBLICAS Y RESERVAS WEB
# ========================================================

def index(request):
    tipos = TipoHabitacion.objects.all()
    habitaciones = Habitación.objects.all()
    cliente_nombre = None
    reserva_activa = None
    folio_huesped = None

    if request.user.is_authenticated:
        c = Cliente.objects.filter(email=request.user.email).first()
        cliente_nombre = c.nombre_completo if c else request.user.first_name or request.user.username
        
        # Buscar la reserva activa más reciente del huésped
        if c:
            reserva_activa = Reserva.objects.filter(cliente=c).exclude(estado='CheckOut').order_by('-id').first()
            if reserva_activa and hasattr(reserva_activa, 'folio'):
                folio_huesped = reserva_activa.folio

    return render(request, 'publico/index.html', {
        'tipos': tipos,
        'habitaciones': habitaciones,
        'cliente_nombre': cliente_nombre,
        'reserva_activa': reserva_activa,
        'folio_huesped': folio_huesped,
    })

def buscar_disponibilidad_api(request):
    disponibles = Habitación.objects.filter(estado='Disponible').select_related('tipo')
    data = []
    for h in disponibles:
        data.append({
            'numero': h.numero,
            'tipo': h.tipo.nombre,
            'precio': int(h.tipo.precio_base),
            'capacidad': h.tipo.capacidad_personas,
            'descripcion': h.tipo.descripcion or '',
            'imagen': h.tipo.imagen_url or ''
        })
    return JsonResponse({'status': 'ok', 'habitaciones': data})

# ========================================================
# REGISTRO Y AUTH HUÉSPED (SEGURIDAD CHILE: LEY 21.719 & OWASP)
# ========================================================

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

    email = data.get('email', '').strip().lower()
    password = data.get('password', '')

    user = authenticate(request, username=email, password=password)
    if user is not None:
        login(request, user)
        cliente = Cliente.objects.filter(email=email).first()
        nombre = cliente.nombre_completo if cliente else user.first_name or user.username
        return JsonResponse({'status': 'ok', 'nombre': nombre, 'email': email})
    else:
        return JsonResponse({'status': 'error', 'message': 'Correo o contraseña incorrectos. Por favor verifique sus datos.'}, status=400)

@require_POST
def cliente_logout_api(request):
    logout(request)
    return JsonResponse({'status': 'ok', 'message': 'Sesión cerrada.'})

@require_POST
def reservar_publico_api(request):
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Datos malformados.'}, status=400)

    numero_hab = data.get('habitacion_id')
    nombre = data.get('nombre')
    email = data.get('email')
    checkin_str = data.get('checkin')
    checkout_str = data.get('checkout')

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
    if hab.estado != 'Disponible':
        return JsonResponse({'status': 'error', 'message': 'La habitación ya no se encuentra disponible.'}, status=400)

    with transaction.atomic():
        cliente, _ = Cliente.objects.get_or_create(
            email=email,
            defaults={'nombre_completo': nombre}
        )
        codigo = f"RES-{hab.numero}-{int(timezone.now().timestamp()) % 10000}"
        reserva = Reserva.objects.create(
            codigo_reserva=codigo,
            cliente=cliente,
            habitacion=hab,
            fecha_checkin=checkin_str or datetime.date.today(),
            fecha_checkout=checkout_str or (datetime.date.today() + datetime.timedelta(days=1)),
            estado='Confirmada'
        )
        folio = Folio.objects.create(reserva=reserva)
        Cargo.objects.create(folio=folio, descripcion=f"Alojamiento {hab.tipo.nombre}", monto=hab.tipo.precio_base)
        hab.estado = 'Ocupada'
        hab.save()

    return JsonResponse({'status': 'ok', 'message': f'¡Reserva {codigo} confirmada exitosamente a nombre de {nombre}!'})

# ========================================================
# AUTOSERVICIO DEL HUÉSPED (PEDIR SERVICIOS EXTRAS Y ABONAR WEBPAY)
# ========================================================

@login_required
@require_POST
def huesped_solicitar_servicio(request):
    c = Cliente.objects.filter(email=request.user.email).first()
    if not c:
        return JsonResponse({'status': 'error', 'message': 'Perfil de huésped no encontrado.'}, status=400)

    reserva = Reserva.objects.filter(cliente=c).exclude(estado='CheckOut').order_by('-id').first()
    if not reserva or not hasattr(reserva, 'folio'):
        return JsonResponse({'status': 'error', 'message': 'No tienes una estadía activa para cargar servicios.'}, status=400)

    data = json.loads(request.body)
    servicio = data.get('servicio', 'Servicio a la Habitación')
    monto = int(data.get('monto', 15000))

    with transaction.atomic():
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

    data = json.loads(request.body)
    monto = int(data.get('monto', 0))
    if monto <= 0:
        return JsonResponse({'status': 'error', 'message': 'Monto de pago inválido.'}, status=400)

    with transaction.atomic():
        Abono.objects.create(folio=reserva.folio, descripcion='Pago Online WebPay (Transbank)', monto=monto, metodo_pago='WebPay Plus')

    return JsonResponse({'status': 'ok', 'message': f'¡Pago de ${monto:,} CLP procesado exitosamente vía WebPay!'})

# ========================================================
# AUTENTICACIÓN ADMIN / STAFF (RNF-04)
# ========================================================

def login_admin_view(request):
    if request.user.is_authenticated and request.user.groups.filter(name__in=['recepcion', 'housekeeping', 'mantenimiento']).exists():
        return redirect('panel_operativo')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        user = authenticate(request, username=email, password=password)
        if user is not None:
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
    rol = obtener_rol_usuario(request.user)
    habitaciones = Habitación.objects.all().select_related('tipo').order_by('numero')

    total = habitaciones.count()
    disponibles = habitaciones.filter(estado='Disponible').count()
    ocupadas = habitaciones.filter(estado='Ocupada').count()
    sucias = habitaciones.filter(estado='Sucia').count()
    en_limpieza = habitaciones.filter(estado='EnLimpieza').count()
    mantenimiento = habitaciones.filter(estado='Mantenimiento').count()
    ocupacion_pct = int((ocupadas / total * 100)) if total > 0 else 0

    return render(request, 'admin/panel.html', {
        'rol': rol,
        'habitaciones': habitaciones,
        'total': total,
        'disponibles': disponibles,
        'ocupadas': ocupadas,
        'sucias': sucias,
        'en_limpieza': en_limpieza,
        'mantenimiento': mantenimiento,
        'ocupacion_pct': ocupacion_pct,
    })

# ========================================================
# ENDPOINTS OPERATIVOS CON SEGURIDAD (RBAC)
# ========================================================

@login_required
def get_room_folio(request, numero):
    if not es_recepcionista(request.user):
        return HttpResponseForbidden("Acceso denegado: solo personal de Recepción puede ver folios.")

    hab = get_object_or_404(Habitación, numero=numero)
    reserva_activa = hab.reservas.filter(estado__in=['Confirmada', 'CheckIn']).last()
    
    folio_data = None
    if reserva_activa and hasattr(reserva_activa, 'folio'):
        f = reserva_activa.folio
        folio_data = {
            'guest': reserva_activa.cliente.nombre_completo,
            'email': reserva_activa.cliente.email,
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

    Abono.objects.create(folio=reserva.folio, descripcion='Abono en Caja (RF-02)', monto=monto)
    return JsonResponse({'status': 'ok', 'message': 'Abono registrado con éxito.'})

@login_required
@require_POST
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
        TareaLimpieza.objects.create(habitacion=hab, estado='Pendiente')

    return JsonResponse({'status': 'ok', 'message': 'Check-out listo. Habitación enviada a Housekeeping (SUCIA).'})

@login_required
@require_POST
def reportar_falla(request, numero):
    hab = get_object_or_404(Habitación, numero=numero)
    data = json.loads(request.body)
    desc = data.get('descripcion', 'Falla técnica no especificada')

    with transaction.atomic():
        hab.estado = 'Mantenimiento'
        hab.ticket_falla = desc
        hab.save()
        OrdenMantenimiento.objects.create(habitacion=hab, descripcionfalla=desc, reportado_por=request.user)

    return JsonResponse({'status': 'ok', 'message': 'Falla registrada y habitación bloqueada preventivamente.'})

@login_required
@require_POST
def cambiar_estado_aseo(request, numero):
    if not es_housekeeping(request.user):
        return HttpResponseForbidden("Acceso denegado: solo personal de Housekeeping.")

    hab = get_object_or_404(Habitación, numero=numero)
    data = json.loads(request.body)
    accion = data.get('accion')

    with transaction.atomic():
        if accion == 'iniciar':
            hab.estado = 'EnLimpieza'
            hab.save()
            tarea, _ = TareaLimpieza.objects.get_or_create(habitacion=hab, estado__in=['Pendiente', 'EnProceso'])
            tarea.estado = 'EnProceso'
            tarea.responsable = request.user
            tarea.save()
        elif accion == 'finalizar':
            hab.estado = 'Disponible'
            hab.save()
            tarea = TareaLimpieza.objects.filter(habitacion=hab, estado='EnProceso').first()
            if tarea:
                tarea.estado = 'Finalizada'
                tarea.sabanas_cambiadas = True
                tarea.toallas_repuestas = True
                tarea.bano_desinfectado = True
                tarea.amenities_completos = True
                tarea.piso_aspirado = True
                tarea.save()

    return JsonResponse({'status': 'ok', 'estado': hab.estado})

@login_required
@require_POST
def resolver_mantenimiento(request, numero):
    if not es_mantenimiento(request.user):
        return HttpResponseForbidden("Acceso denegado: solo personal de Mantenimiento.")

    hab = get_object_or_404(Habitación, numero=numero)
    with transaction.atomic():
        orden = OrdenMantenimiento.objects.filter(habitacion=hab, estado='Abierta').last()
        if orden:
            orden.estado = 'Resuelta'
            orden.fecha_resolucion = timezone.now()
            orden.save()

        hab.estado = 'Sucia'
        hab.ticket_falla = None
        hab.save()
        TareaLimpieza.objects.create(habitacion=hab, estado='Pendiente')

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

    # En producción aquí se envía correo vía SMTP o se guarda en BD
    return JsonResponse({
        'status': 'ok',
        'message': f'¡Gracias {nombre}! Tu mensaje ha sido enviado exitosamente a nuestro equipo de atención.'
    })
