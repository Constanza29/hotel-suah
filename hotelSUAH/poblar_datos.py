import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hotelSUAH.settings')
django.setup()

from django.contrib.auth.models import User, Group
from habitaciones.models import TipoHabitacion, Habitación
from reservas.models import Cliente, Reserva, Folio, Cargo, Abono
from operaciones.models import OrdenMantenimiento, TareaLimpieza
import datetime

print("Iniciando carga de datos iniciales...")

# 1. Crear Grupos / Roles RBAC
roles = ['recepcion', 'housekeeping', 'mantenimiento', 'cliente']
grupos = {}
for r in roles:
    g, _ = Group.objects.get_or_create(name=r)
    grupos[r] = g

# 2. Crear Usuarios Empleados Demo (igual que en el prototipo)
# Superuser admin
if not User.objects.filter(username='admin').exists():
    admin = User.objects.create_superuser('admin', 'admin@hotel.cl', 'admin123')
    print("Admin creado: admin / admin123")

# Recepcionista
if not User.objects.filter(username='rep@hotel.cl').exists():
    u_rep = User.objects.create_user('rep@hotel.cl', 'rep@hotel.cl', '1234', first_name='Recepcionista')
    u_rep.groups.add(grupos['recepcion'])
    print("Recepcionista creado: rep@hotel.cl / 1234")

# Housekeeping
if not User.objects.filter(username='aseo@hotel.cl').exists():
    u_aseo = User.objects.create_user('aseo@hotel.cl', 'aseo@hotel.cl', '1234', first_name='Camarera Limpieza')
    u_aseo.groups.add(grupos['housekeeping'])
    print("Aseo creado: aseo@hotel.cl / 1234")

# Mantenimiento
if not User.objects.filter(username='mant@hotel.cl').exists():
    u_mant = User.objects.create_user('mant@hotel.cl', 'mant@hotel.cl', '1234', first_name='Técnico Mantención')
    u_mant.groups.add(grupos['mantenimiento'])
    print("Mantenimiento creado: mant@hotel.cl / 1234")

# 3. Crear Tipos de Habitación
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

# 4. Crear Habitaciones y Data inicial exacta al prototipo
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

    # Si tiene ticket de mantenimiento, crear la orden
    if item['ticket']:
        OrdenMantenimiento.objects.get_or_create(
            habitacion=hab,
            descripcion_falla=item['ticket'],
            defaults={'estado': 'Abierta'}
        )

    # Si está Sucia o En Limpieza, crear TareaLimpieza
    if item['estado'] in ['Sucia', 'EnLimpieza']:
        st = 'EnProceso' if item['estado'] == 'EnLimpieza' else 'Pendiente'
        TareaLimpieza.objects.get_or_create(
            habitacion=hab,
            defaults={'estado': st}
        )

    # Si está ocupada, crear cliente, reserva y folio
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
                'fecha_checkout': today + datetime.timedelta(days=1),
                'num_huespedes': 2,
                'estado': 'CheckIn'
            }
        )
        folio, _ = Folio.objects.get_or_create(reserva=reserva)
        # Limpiar y agregar cargos / abonos
        folio.cargos.all().delete()
        folio.abonos.all().delete()
        for desc, monto in item.get('cargos', []):
            Cargo.objects.create(folio=folio, descripcion=desc, monto=monto)
        for desc, monto in item.get('abonos', []):
            Abono.objects.create(folio=folio, descripcion=desc, monto=monto)

print("Datos iniciales cargados con éxito!")
