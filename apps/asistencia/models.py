from django.db import models
from apps.usuarios.models import Usuario
from apps.academia.models import Actividad

class RegistroAsistencia(models.Model):
    """
    Registro simple de presencia del alumno.
    """
    alumno = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name="asistencias",
    )
    actividad = models.ForeignKey(
        Actividad, 
        on_delete=models.CASCADE, 
        related_name="asistencias",
        null=True,
        blank=True
    )
    clase = models.ForeignKey(
        'academia.Cronograma', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="asistencias_sesion"
    )
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Asistencia"
        verbose_name_plural = "02.2 - Registro de Asistencias"
        ordering = ["-fecha_hora"]
        db_table = 'core_asistencia'

    def __str__(self):
        fecha = self.fecha_hora.strftime("%d/%m/%Y %H:%M")
        return f"Asistencia de {self.alumno.nombre_completo} - {fecha}"
