from django.db import models
from django.contrib.auth.models import User
from habitaciones.models import Habitación

class TareaLimpieza(models.Model):
    """
    Checklist móvil de limpieza e insumos (RF-03).
    """
    ESTADOS = [
        ('Pendiente', 'Pendiente'),
        ('EnProceso', 'En Proceso'),
        ('Finalizada', 'Finalizada (Limpia)'),
    ]

    habitacion = models.ForeignKey(Habitación, on_delete=models.CASCADE, related_name='tareas_limpieza')
    responsable = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='tareas_asignadas')
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Pendiente')
    
    # Checklist de insumos y puntos de control
    sabanas_cambiadas = models.BooleanField(default=False)
    toallas_repuestas = models.BooleanField(default=False)
    bano_desinfectado = models.BooleanField(default=False)
    amenities_completos = models.BooleanField(default=False)
    piso_aspirado = models.BooleanField(default=False)
    
    observaciones = models.TextField(blank=True, null=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Limpieza Hab {self.habitacion.numero} - {self.estado}"

    class Meta:
        verbose_name = "Tarea de Limpieza"
        verbose_name_plural = "Tareas de Limpieza"


class OrdenMantenimiento(models.Model):
    """
    Bloqueo y registro de fallas de mantenimiento (RF-04).
    """
    ESTADOS = [
        ('Abierta', 'Falla Activa (Habitación Bloqueada)'),
        ('EnReparacion', 'En Reparación'),
        ('Resuelta', 'Resuelta (Desbloquear)'),
    ]

    habitacion = models.ForeignKey(Habitación, on_delete=models.CASCADE, related_name='ordenes_mantenimiento')
    reportado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='fallas_reportadas')
    descripcion_falla = models.TextField() # Ej: Falla eléctrica en AC
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Abierta')
    fecha_reporte = models.DateTimeField(auto_now_add=True)
    fecha_resolucion = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Orden #{self.id} Hab {self.habitacion.numero}: {self.descripcion_falla[:30]} ({self.estado})"

    class Meta:
        verbose_name = "Orden de Mantenimiento"
        verbose_name_plural = "Órdenes de Mantenimiento"
