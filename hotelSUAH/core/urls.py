from django.urls import path
from core import views

urlpatterns = [
    path('', views.index, name='index'),
    path('api/buscar-disponibilidad/', views.buscar_disponibilidad_api, name='buscar_disponibilidad'),
    path('api/reservar-publico/', views.reservar_publico_api, name='reservar_publico'),

    path('api/cliente/registro/', views.cliente_registro_api, name='cliente_registro_api'),
    path('api/cliente/login/', views.cliente_login_api, name='cliente_login_api'),
    path('api/cliente/logout/', views.cliente_logout_api, name='cliente_logout_api'),

    path('api/huesped/solicitar-servicio/', views.huesped_solicitar_servicio, name='huesped_solicitar_servicio'),
    path('api/huesped/abono-online/', views.huesped_abono_online, name='huesped_abono_online'),
    path('webpay/retorno/', views.webpay_retorno_view, name='webpay_retorno'),

    path('login-admin/', views.login_admin_view, name='login_admin'),
    path('logout-admin/', views.logout_admin_view, name='logout_admin'),
    path('panel/', views.panel_operativo, name='panel_operativo'),

    path('api/folio/<str:numero>/', views.get_room_folio, name='get_room_folio'),
    path('api/consumo/<str:numero>/', views.agregar_consumo, name='agregar_consumo'),
    path('api/abono/<str:numero>/', views.abonar_folio, name='abonar_folio'),
    path('api/checkin/<str:numero>/', views.checkin_manual, name='checkin_manual'),
    path('api/checkout/<str:numero>/', views.finalizar_checkout, name='finalizar_checkout'),
    path('api/reportar-falla/<str:numero>/', views.reportar_falla, name='reportar_falla'),
    path('api/aseo/<str:numero>/', views.cambiar_estado_aseo, name='cambiar_estado_aseo'),
    path('api/recepcion/solicitar-aseo/<str:numero>/', views.recepcion_solicitar_aseo_ocupada, name='recepcion_solicitar_aseo_ocupada'),
    path('api/housekeeping/atender-solicitud/<int:tarea_id>/', views.atender_solicitud_aseo_ocupada, name='atender_solicitud_aseo_ocupada'),
    path('api/resolver-mantenimiento/<str:numero>/', views.resolver_mantenimiento, name='resolver_mantenimiento'),
    path('api/contacto/enviar/', views.enviar_mensaje_contacto_api, name='enviar_mensaje_contacto'),
    path('api/contacto/responder/<int:mensaje_id>/', views.responder_mensaje_contacto_api, name='responder_mensaje_contacto'),
    path('api/housekeeping/asignar-tarea/<int:tarea_id>/', views.asignar_tarea_aseo, name='asignar_tarea_aseo'),
    path('api/mantenimiento/asignar-orden/<int:orden_id>/', views.asignar_orden_mantenimiento, name='asignar_orden_mantenimiento'),
    path('api/personal/crear/', views.crear_personal_api, name='crear_personal_api'),
    path('api/recepcion/consultar-disponibilidad/', views.consultar_disponibilidad_recepcion_api, name='consultar_disponibilidad_recepcion'),
]
