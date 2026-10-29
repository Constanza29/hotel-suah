from django.db import models
from django.contrib.auth.models import User
from habitaciones.models import Habitación

class Cliente(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True, related_name='perfil_cliente')
    nombre_completo = models.CharField(max_length=150)
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    rut = models.CharField(max_length=12, blank=True, null=True)

    def __str__(self):
        return f"{self.nombre_completo} ({self.email})"

    class Meta:
        verbose_name = "Cliente / Huésped"
        verbose_name_plural = "Clientes / Huéspedes"


class Reserva(models.Model):
    ESTADOS = [
        ('Pendiente', 'Pendiente'),
        ('Confirmada', 'Confirmada'),
        ('CheckIn', 'Check-In Realizado'),
        ('CheckOut', 'Check-Out Finalizado'),
        ('Cancelada', 'Cancelada'),
    ]

    codigo_reserva = models.CharField(max_length=20, unique=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='reservas')
    habitacion = models.ForeignKey(Habitación, on_delete=models.CASCADE, related_name='reservas')
    fecha_checkin = models.DateField()
    fecha_checkout = models.DateField()
    num_huespedes = models.PositiveIntegerField(default=1)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Confirmada')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Reserva {self.codigo_reserva} - Hab {self.habitacion.numero} ({self.cliente.nombre_completo})"

    class Meta:
        verbose_name = "Reserva"
        verbose_name_plural = "Reservas"


class Folio(models.Model):
    """
    Representa la cuenta de cobro asociada a una reserva/habitación.
    Soporta cargos por consumo y pagos/abonos (RF-02 y RF-05).
    """
    reserva = models.OneToOneField(Reserva, on_delete=models.CASCADE, related_name='folio')
    abierto = models.BooleanField(default=True)
    fecha_apertura = models.DateTimeField(auto_now_add=True)
    fecha_cierre = models.DateTimeField(null=True, blank=True)

    @property
    def total_cargos(self):
        return sum(c.monto for c in self.cargos.all())

    @property
    def total_abonos(self):
        return sum(a.monto for a in self.abonos.all())

    @property
    def saldo_pendiente(self):
        return self.total_cargos - self.total_abonos

    def __str__(self):
        return f"Folio {self.id} - Reserva {self.reserva.codigo_reserva} (Saldo: ${self.saldo_pendiente:,} CLP)"


class Cargo(models.Model):
    folio = models.ForeignKey(Folio, on_delete=models.CASCADE, related_name='cargos')
    descripcion = models.CharField(max_length=200) # Ej: Alojamiento (2 noches), Room Service
    monto = models.DecimalField(max_digits=10, decimal_places=0)
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"+ ${self.monto:,} - {self.descripcion}"


class Abono(models.Model):
    folio = models.ForeignKey(Folio, on_delete=models.CASCADE, related_name='abonos')
    descripcion = models.CharField(max_length=200) # Ej: Abono Inicial Reserva, Pago Caja
    monto = models.DecimalField(max_digits=10, decimal_places=0)
    metodo_pago = models.CharField(max_length=50, default='Efectivo/Transferencia')
    fecha = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"- ${self.monto:,} - {self.descripcion}"
