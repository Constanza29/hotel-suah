from django.contrib import admin
from .models import Cliente, Reserva, Folio, Cargo, Abono

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombre_completo', 'email', 'telefono', 'rut')
    search_fields = ('nombre_completo', 'email', 'rut')

class CargoInline(admin.TabularInline):
    model = Cargo
    extra = 1

class AbonoInline(admin.TabularInline):
    model = Abono
    extra = 1

@admin.register(Folio)
class FolioAdmin(admin.ModelAdmin):
    list_display = ('id', 'reserva', 'saldo_pendiente', 'abierto', 'fecha_apertura')
    inlines = [CargoInline, AbonoInline]

@admin.register(Reserva)
class ReservaAdmin(admin.ModelAdmin):
    list_display = ('codigo_reserva', 'cliente', 'habitacion', 'fecha_checkin', 'fecha_checkout', 'estado')
    list_filter = ('estado', 'fecha_checkin')
    search_fields = ('codigo_reserva', 'cliente__nombre_completo', 'habitacion__numero')
