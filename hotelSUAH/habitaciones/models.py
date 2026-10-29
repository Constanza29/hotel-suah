from django.db import models

class TipoHabitacion(models.Model):
    nombre = models.CharField(max_length=50, unique=True) # Estándar, Suite, Suite Premium
    descripcion = models.TextField(blank=True, null=True)
    precio_base = models.DecimalField(max_digits=10, decimal_places=0) # CLP
    capacidad_personas = models.PositiveIntegerField(default=2)
    imagen_url = models.URLField(blank=True, null=True)

    def __str__(self):
        return f"{self.nombre} - ${self.precio_base:,} CLP"

    class Meta:
        verbose_name = "Tipo de Habitación"
        verbose_name_plural = "Tipos de Habitaciones"


class Habitación(models.Model):
    ESTADOS = [
        ('Disponible', 'Disponible'),
        ('Ocupada', 'Ocupada'),
        ('Sucia', 'Sucia'),
        ('EnLimpieza', 'En Limpieza'),
        ('Mantenimiento', 'Mantenimiento'),
    ]

    numero = models.CharField(max_length=10, unique=True, primary_key=True) # Ej: 101, 102
    tipo = models.ForeignKey(TipoHabitacion, on_delete=models.CASCADE, related_name='habitaciones')
    piso = models.IntegerField(default=1)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Disponible')
    ticket_falla = models.TextField(blank=True, null=True) # Falla activa si está en Mantenimiento

    def __str__(self):
        return f"Habitación {self.numero} ({self.tipo.nombre}) - {self.estado}"

    class Meta:
        verbose_name = "Habitación"
        verbose_name_plural = "Habitaciones"
        ordering = ['numero']
