from django.contrib import admin
from .models import TipoHabitacion, Habitación

@admin.register(TipoHabitacion)
class TipoHabitacionAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'precio_base', 'capacidad_personas')

@admin.register(Habitación)
class HabitacionAdmin(admin.ModelAdmin):
    list_display = ('numero', 'tipo', 'piso', 'estado', 'ticket_falla')
    list_filter = ('estado', 'tipo', 'piso')
    search_fields = ('numero',)
