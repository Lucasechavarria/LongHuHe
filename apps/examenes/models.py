from django.db import models, transaction
from apps.usuarios.models import Usuario, Grado, Examen

class MesaExamen(models.Model):
    """ Convocatoria formal a examen (RF7.1) """
    fecha = models.DateTimeField()
    lugar = models.CharField(max_length=200, help_text="Sede o Dirección del evento")
    examinadores = models.ManyToManyField(Usuario, related_name="mesas_examinadoras", limit_choices_to={'es_profe': True})
    maestro_invitado = models.CharField(max_length=200, blank=True, help_text="Para maestros externos a la app")
    esta_abierta = models.BooleanField(default=True, help_text="Permite inscripciones")
    finalizada = models.BooleanField(default=False, help_text="Marca el evento como cerrado")

    class Meta:
        verbose_name = "Mesa de Examen"
        verbose_name_plural = "06.1 - Mesas de Examen"
        ordering = ['-fecha']

    def __str__(self):
        return f"Mesa {self.fecha.strftime('%d/%m/%Y')} - {self.lugar}"

class InscripcionExamen(models.Model):
    """ Candidato a una mesa (RF7.2) """
    class EstadoResultado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente de Evaluar"
        APROBADO = "aprobado", "Aprobado / Ascenso"
        DESAPROBADO = "desaprobado", "Desaprobado"
        AUSENTE = "ausente", "Ausente"

    mesa = models.ForeignKey(MesaExamen, on_delete=models.CASCADE, related_name="candidatos")
    alumno = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="inscripciones_examenes")
    grado_actual = models.ForeignKey(Grado, on_delete=models.PROTECT, related_name="+")
    grado_a_aspirar = models.ForeignKey(Grado, on_delete=models.PROTECT, related_name="+")
    
    resultado = models.CharField(max_length=20, choices=EstadoResultado.choices, default=EstadoResultado.PENDIENTE)
    nota_tecnica = models.PositiveIntegerField(blank=True, null=True, help_text="Puntaje 0-100")
    observaciones = models.TextField(blank=True)
    fecha_inscripcion = models.DateTimeField(auto_now_add=True)
    procesado = models.BooleanField(default=False, help_text="Indica si ya se aplicó el ascenso en el perfil")

    class Meta:
        verbose_name = "Candidato a Examen"
        verbose_name_plural = "06.2 - Candidatos e Inscripciones"
        unique_together = ('mesa', 'alumno')

    def __str__(self):
        try:
            alumno_str = self.alumno.nombre_completo if self.alumno else "Alumno desconocido"
            grado_str = self.grado_a_aspirar.nombre if self.grado_a_aspirar else "N/A"
            return f"{alumno_str} -> {grado_str}"
        except Exception:
            return f"Inscripción Examen #{self.id}"

    @transaction.atomic
    def aplicar_ascenso(self):
        """ Task 7.3: Automatización de ascenso de grado y nivel de acceso """
        if self.resultado == self.EstadoResultado.APROBADO and not self.procesado:
            alumno = self.alumno
            
            # 1. Actualización Atómica del Alumno
            alumno.grado = self.grado_a_aspirar
            # Desbloqueo de nivel según el nuevo grado
            if self.grado_a_aspirar.nivel_desbloqueado:
                alumno.nivel_acceso = self.grado_a_aspirar.nivel_desbloqueado
            
            alumno.save(update_fields=['grado', 'nivel_acceso'])
            
            # 2. Registro histórico
            Examen.objects.create(
                alumno=alumno,
                grado=self.grado_a_aspirar,
                fecha=self.mesa.fecha.date(),
                examinador=self.mesa.examinadores.first(),
                examinador_externo=self.mesa.maestro_invitado,
                observaciones=f"Aprobado en Mesa {self.mesa.id}. Nota: {self.nota_tecnica or 'N/A'}. {self.observaciones}"
            )
            
            self.procesado = True
            # No llamamos a self.save() aquí para evitar recursión.
            # El llamador (save() o admin action) se encarga de persistir self.procesado.

    def save(self, *args, **kwargs):
        # 1. Guardado base
        super().save(*args, **kwargs)
        
        # 2. Disparar ascenso si está aprobado y no procesado
        if self.resultado == self.EstadoResultado.APROBADO and not self.procesado:
            self.aplicar_ascenso()
            # Persistimos el flag procesado sin re-disparar save() completo
            InscripcionExamen.objects.filter(pk=self.pk).update(procesado=True)
