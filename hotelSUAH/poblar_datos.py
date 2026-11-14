import os
import datetime
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotelSUAH.settings')
django.setup()

from django.contrib.auth.models import User, Group
from habitaciones.models import TipoHabitacion, Habitación
from reservas.models import Cliente, Reserva, Folio, Cargo, Abono
from operaciones.models import OrdenMantenimiento, TareaLimpieza

print("Iniciando carga de datos iniciales...")

roles = ['recepcion', 'housekeeping', 'mantenimiento', 'cliente']
grupos = {}
for r in roles:
    g, _ = Group.objects.get_or_create(name=r)
    grupos[r] = g

personal_staff = [
    ('admin@suah.cl', 'Constanza', 'Cortés', 'admin', 'admin123', True),
    ('rep@suah.cl', 'Matías', 'Sepúlveda', 'recepcion', '1234', False),
    ('valentina.soto@suah.cl', 'Valentina', 'Soto', 'recepcion', '1234', False),
    ('aseo@suah.cl', 'Marta', 'Henríquez', 'housekeeping', '1234', False),
    ('camila.vega@suah.cl', 'Camila', 'Vega', 'housekeeping', '1234', False),
    ('rosa.morales@suah.cl', 'Rosa', 'Morales', 'housekeeping', '1234', False),
    ('mant@suah.cl', 'Jorge', 'Valenzuela', 'mantenimiento', '1234', False),
    ('pedro.araya@suah.cl', 'Pedro', 'Araya', 'mantenimiento', '1234', False),
]

for email, fn, ln, rol, pwd, es_super in personal_staff:
    u = User.objects.filter(username=email).first()
    if not u:
        if es_super:
            u = User.objects.create_superuser(email, email, pwd, first_name=fn, last_name=ln)
        else:
            u = User.objects.create_user(email, email, pwd, first_name=fn, last_name=ln)
    else:
        u.first_name = fn
        u.last_name = ln
        u.save()

    if rol in grupos:
        u.groups.clear()
        u.groups.add(grupos[rol])
    print(f"Personal: {fn} {ln} ({email}) - Rol: {rol}")

if not User.objects.filter(username='cliente@suah.cl').exists():
    u_cli = User.objects.create_user('cliente@suah.cl', 'cliente@suah.cl', 'Cliente123!', first_name='Constanza Cortés')
    u_cli.groups.add(grupos['cliente'])
    Cliente.objects.get_or_create(
        user=u_cli,
        email='cliente@suah.cl',
        defaults={'nombre_completo': 'Constanza Cortés', 'telefono': '+56 9 8765 4321', 'rut': '12.345.678-5'}
    )
    print("Cliente demo creado: cliente@suah.cl / Cliente123!")

tipo_estandar, _ = TipoHabitacion.objects.get_or_create(
    nombre='Estándar',
    defaults={
        'precio_base': 65000,
        'capacidad_personas': 2,
        'descripcion': 'Ideal para estadías cortas o viajes de negocio. Cama King, Wi-Fi 6 y baño privado.',
        'imagen_url': 'https://images.unsplash.com/photo-1611892440504-42a792e24d32?auto=format&fit=crop&w=800&q=80'
    }
)

tipo_suite, _ = TipoHabitacion.objects.get_or_create(
    nombre='Suite',
    defaults={
        'precio_base': 95000,
        'capacidad_personas': 3,
        'descripcion': 'Amplitud, confort y vistas panorámicas a la ciudad con sala de estar integrada.',
        'imagen_url': 'https://images.unsplash.com/photo-1566665797739-1674de7a421a?auto=format&fit=crop&w=800&q=80'
    }
)

tipo_premium, _ = TipoHabitacion.objects.get_or_create(
    nombre='Suite Premium',
    defaults={
        'precio_base': 150000,
        'capacidad_personas': 4,
        'descripcion': 'Máximo lujo con jacuzzi privado, terraza panorámica, minibar libre y servicio VIP.',
        'imagen_url': 'https://images.unsplash.com/photo-1590490359683-658d3d23f972?auto=format&fit=crop&w=800&q=80'
    }
)

data_habitaciones = [
    {'numero': '101', 'tipo': tipo_estandar, 'piso': 1, 'estado': 'Disponible', 'ticket': None},
    {'numero': '102', 'tipo': tipo_estandar, 'piso': 1, 'estado': 'Ocupada', 'ticket': None,
     'guest': 'Juan Pérez', 'guest_email': 'juan@example.com',
     'cargos': [('Alojamiento (2 noches)', 130000), ('Room Service (Cena)', 25000)],
     'abonos': [('Abono Inicial Reserva', 50000)]},
    {'numero': '103', 'tipo': tipo_estandar, 'piso': 1, 'estado': 'Ocupada', 'ticket': None,
     'guest': 'María Salas', 'guest_email': 'maria@example.com',
     'cargos': [('Alojamiento (1 noche)', 65000)],
     'abonos': []},
    {'numero': '104', 'tipo': tipo_estandar, 'piso': 1, 'estado': 'Sucia', 'ticket': None},
    {'numero': '201', 'tipo': tipo_suite, 'piso': 2, 'estado': 'EnLimpieza', 'ticket': None},
    {'numero': '202', 'tipo': tipo_suite, 'piso': 2, 'estado': 'Disponible', 'ticket': None},
    {'numero': '301', 'tipo': tipo_premium, 'piso': 3, 'estado': 'Mantenimiento', 'ticket': 'Falla eléctrica en AC'},
    {'numero': '302', 'tipo': tipo_premium, 'piso': 3, 'estado': 'Disponible', 'ticket': None},
]

today = datetime.date.today()

for item in data_habitaciones:
    hab, _ = Habitación.objects.get_or_create(
        numero=item['numero'],
        defaults={'tipo': item['tipo'], 'piso': item['piso'], 'estado': item['estado'], 'ticket_falla': item['ticket']}
    )
    hab.estado = item['estado']
    hab.ticket_falla = item['ticket']
    hab.save()

    if item['ticket']:
        if not OrdenMantenimiento.objects.filter(habitacion=hab, descripcion_falla=item['ticket']).exists():
            OrdenMantenimiento.objects.create(
                habitacion=hab,
                descripcion_falla=item['ticket'],
                estado='Abierta'
            )

    if item['estado'] in ['Sucia', 'EnLimpieza']:
        st = 'EnProceso' if item['estado'] == 'EnLimpieza' else 'Pendiente'
        if not TareaLimpieza.objects.filter(habitacion=hab, estado=st).exists():
            TareaLimpieza.objects.create(
                habitacion=hab,
                estado=st
            )

    if item.get('guest'):
        cliente, _ = Cliente.objects.get_or_create(
            email=item['guest_email'],
            defaults={'nombre_completo': item['guest'], 'telefono': '+56 9 1234 5678'}
        )
        reserva, _ = Reserva.objects.get_or_create(
            codigo_reserva=f"RES-{hab.numero}",
            defaults={
                'cliente': cliente,
                'habitacion': hab,
                'fecha_checkin': today - datetime.timedelta(days=1),
                'fecha_checkout': today + datetime.timedelta(days=2),
                'num_huespedes': 2,
                'estado': 'CheckIn'
            }
        )
        reserva.cliente = cliente
        reserva.habitacion = hab
        reserva.fecha_checkin = today - datetime.timedelta(days=1)
        reserva.fecha_checkout = today + datetime.timedelta(days=2)
        reserva.estado = 'CheckIn'
        reserva.save()

        folio, _ = Folio.objects.get_or_create(reserva=reserva)
        folio.abierto = True
        folio.fecha_cierre = None
        folio.save()
        folio.cargos.all().delete()
        folio.abonos.all().delete()
        for desc, monto in item.get('cargos', []):
            Cargo.objects.create(folio=folio, descripcion=desc, monto=monto)
        for desc, monto in item.get('abonos', []):
            Abono.objects.create(folio=folio, descripcion=desc, monto=monto)

print("Datos iniciales cargados con éxito!")
