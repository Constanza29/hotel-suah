from django.urls import path
from core import views

urlpatterns = [
    # Vista pública y buscador
    path('', views.index, name='index'),
    path('api/buscar-disponibilidad/', views.buscar_disponibilidad_api, name='buscar_disponibilidad'),
    path('api/reservar-publico/', views.reservar_publico_api, name='reservar_publico'),

    # Auth Clientes / Huéspedes Web
    path('api/cliente/registro/', views.cliente_registro_api, name='cliente_registro_api'),
    path('api/cliente/login/', views.cliente_login_api, name='cliente_login_api'),
    path('api/cliente/logout/', views.cliente_logout_api, name='cliente_logout_api'),

    # Autoservicio Huésped (Servicios extras y abonos online)
    path('api/huesped/solicitar-servicio/', views.huesped_solicitar_servicio, name='huesped_solicitar_servicio'),
    path('api/huesped/abono-online/', views.huesped_abono_online, name='huesped_abono_online'),

    # Auth Empleados / Admin
    path('login-admin/', views.login_admin_view, name='login_admin'),
    path('logout-admin/', views.logout_admin_view, name='logout_admin'),
    path('panel/', views.panel_operativo, name='panel_operativo'),

    # Operaciones Ajax con RBAC
    path('api/folio/<str:numero>/', views.get_room_folio, name='get_room_folio'),
    path('api/consumo/<str:numero>/', views.agregar_consumo, name='agregar_consumo'),
    path('api/abono/<str:numero>/', views.abonar_folio, name='abonar_folio'),
    path('api/checkin/<str:numero>/', views.checkin_manual, name='checkin_manual'),
    path('api/checkout/<str:numero>/', views.finalizar_checkout, name='finalizar_checkout'),
    path('api/reportar-falla/<str:numero>/', views.reportar_falla, name='reportar_falla'),
    path('api/aseo/<str:numero>/', views.cambiar_estado_aseo, name='cambiar_estado_aseo'),
    path('api/resolver-mantenimiento/<str:numero>/', views.resolver_mantenimiento, name='resolver_mantenimiento'),
    path('api/contacto/enviar/', views.enviar_mensaje_contacto_api, name='enviar_mensaje_contacto'),
]
