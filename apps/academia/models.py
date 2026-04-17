from django.db import models
from django.core.exceptions import ValidationError

class Sede(models.Model):
    """
    Lugar físico donde el maestro da clase (antes 'Locación').
    """
    nombre = models.CharField(max_length=120)
    mapa_url = models.URLField("Enlace Google Maps", max_length=500, blank=True, null=True)

    class Meta:
        verbose_name = "Sede"
        verbose_name_plural = "01.1 - Sedes"
        ordering = ["nombre"]
        db_table = 'core_sede'

    @property
    def actividades(self):
        return Actividad.objects.filter(clases_asignadas__sede=self).distinct()

    def __str__(self):
        return self.nombre

class Actividad(models.Model):
    """
    Actividades ofrecidas por la escuela (Tai-Chi, Kung-Fu, Defensa Personal, etc.)
    """
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    precio_mes = models.DecimalField("Precio Mensual", max_digits=10, decimal_places=2, default=0)
    precio_clase = models.DecimalField("Precio Clase Suelta", max_digits=10, decimal_places=2, default=0)
    color_etiqueta = models.CharField(
        "Color Hex", max_length=7, default="#f97316",
        help_text="Color para diferenciar la actividad en el cronograma. (Ej: #3b82f6)"
    )

    class Meta:
        verbose_name = "Actividad"
        verbose_name_plural = "01.2 - Actividades"
        db_table = 'core_actividad'

    def __str__(self):
        return self.nombre

class Cronograma(models.Model):
    """
    El 'corazón' de la agenda: Vincula Profe + Actividad + Sede + Horario.
    """
    class DiasSemana(models.TextChoices):
        LUNES = "LU", "Lunes"
        MARTES = "MA", "Martes"
        MIERCOLES = "MI", "Miércoles"
        JUEVES = "JU", "Jueves"
        VIERNES = "VI", "Viernes"
        SABADO = "SA", "Sábado"

    profesor = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.CASCADE,
        related_name="clases_dictadas",
        limit_choices_to={'es_profe': True}
    )
    profesor_asistente = models.ForeignKey(
        'usuarios.Usuario', on_delete=models.SET_NULL, null=True, blank=True, 
        related_name="clases_asistente",
        limit_choices_to={'es_profe': True}
    )
    actividad = models.ForeignKey(
        Actividad,
        on_delete=models.CASCADE,
        related_name="clases_asignadas"
    )
    sede = models.ForeignKey(
        Sede,
        on_delete=models.CASCADE,
        related_name="clases_asignadas"
    )
    
    dia = models.CharField("Día de la semana", max_length=2, choices=DiasSemana.choices, default="LU")
    hora_inicio = models.TimeField("Hora de Inicio", null=True, blank=True)
    hora_fin = models.TimeField("Hora de Fin", null=True, blank=True)
    
    cupo = models.PositiveIntegerField("Cupo Máximo", default=20, help_text="Cantidad máxima de alumnos permitidos en este horario.")

    porcentaje_comision_asistente = models.DecimalField(
        " % Comisión Asistente", max_digits=5, decimal_places=2, default=0,
        help_text="Comisión que se lleva el asistente por las ventas registradas en esta clase."
    )
    porcentaje_comision_profesor = models.DecimalField(
        " % Comisión Profesor", max_digits=5, decimal_places=2, default=50,
        help_text="Porcentaje de la cuota o clase que se lleva el profesor principal."
    )

    class Meta:
        verbose_name = "Horario / Clase"
        verbose_name_plural = "01.3 - Cronograma de Clases"
        ordering = ["sede", "dia", "hora_inicio"]
        db_table = 'core_cronograma'

    def __str__(self):
        try:
            horario_str = f"{self.get_dia_display()} {self.hora_inicio.strftime('%H:%M') if self.hora_inicio else '--:--'}"
            act_nombre = self.actividad.nombre if self.actividad else "Sin Actividad"
            sede_nombre = self.sede.nombre if self.sede else "Sin Sede"
            prof_nombre = self.profesor.nombre if self.profesor else "Sin Profesor"
            return f"{act_nombre} ({horario_str}) - {sede_nombre} - Prof. {prof_nombre}"
        except Exception:
            return f"Clase #{self.id} (Error al mostrar detalles)"

class InscripcionClase(models.Model):
    """
    Registro de alumnos anotados a un horario específico del cronograma.
    """
    class EstadoInscrito(models.TextChoices):
        REGULAR = "regular", "Inscrito (Confirmado)"
        ESPERA = "espera", "En Lista de Espera"
        BAJA = "baja", "Dado de Baja"

    alumno = models.ForeignKey('usuarios.Usuario', on_delete=models.CASCADE, related_name="inscripciones_academia")
    clase = models.ForeignKey(Cronograma, on_delete=models.CASCADE, related_name="alumnos_inscritos")
    fecha_inscripcion = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=EstadoInscrito.choices, default=EstadoInscrito.REGULAR)

    class Meta:
        verbose_name = "Inscripción a Clase"
        verbose_name_plural = "01.4 - Inscripciones (Control de Cupo)"
        unique_together = ['alumno', 'clase'] # Un alumno no puede inscribirse 2 veces al mismo horario
        db_table = 'core_inscripcionclase'

    def save(self, *args, **kwargs):
        from django.db import transaction
        # 🛡️ Blindaje: Validar cupo máximo con bloqueo de base de datos
        if not self.pk: # Solo en nuevas inscripciones
            with transaction.atomic():
                # Bloqueamos la fila del cronograma para evitar race conditions
                clase_bloqueada = type(self.clase).objects.select_for_update().get(pk=self.clase.pk)
                Cupo = clase_bloqueada.alumnos_inscritos.filter(estado=self.EstadoInscrito.REGULAR).count()
                if Cupo >= clase_bloqueada.cupo:
                    raise ValidationError(f"No hay cupo disponible para esta clase ({clase_bloqueada.cupo} alumnos máximo).")
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def __str__(self):
        try:
            alumno_str = self.alumno.nombre_completo if self.alumno else "Alumno desconocido"
            clase_str = str(self.clase) if self.clase else "Clase no definida"
            estado_str = self.get_estado_display()
            return f"{alumno_str} -> {clase_str} ({estado_str})"
        except Exception:
            return f"Inscripción #{self.id} (Error al mostrar detalles)"
