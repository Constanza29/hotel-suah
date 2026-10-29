from django.contrib import admin
from .models import TareaLimpieza, OrdenMantenimiento

@admin.register(TareaLimpieza)
class TareaLimpiezaAdmin(admin.ModelAdmin):
    list_display = ('habitacion', 'estado', 'responsable', 'fecha_actualizacion')
    list_filter = ('estado',)

@admin.register(OrdenMantenimiento)
class OrdenMantenimientoAdmin(admin.ModelAdmin):
    list_display = ('id', 'habitacion', 'estado', 'descripcion_falla', 'fecha_reporte')
    list_filter = ('estado',)
