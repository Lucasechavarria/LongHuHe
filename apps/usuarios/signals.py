from django.dispatch import receiver
from apps.examenes.signals import ascenso_aprobado
from apps.usuarios.models import Examen

@receiver(ascenso_aprobado)
def procesar_ascenso(sender, inscripcion, **kwargs):
    """
    Observer que escucha cuando un alumno aprueba un examen.
    Actualiza el grado, nivel de acceso, y crea el historial.
    """
    alumno = inscripcion.alumno
    grado_a_aspirar = inscripcion.grado_a_aspirar
    mesa = inscripcion.mesa
    
    # 1. Actualización del Alumno
    alumno.grado = grado_a_aspirar
    if grado_a_aspirar.nivel_desbloqueado:
        alumno.nivel_acceso = grado_a_aspirar.nivel_desbloqueado
    
    alumno.save(update_fields=['grado', 'nivel_acceso'])
    
    # 2. Registro histórico
    Examen.objects.create(
        alumno=alumno,
        grado=grado_a_aspirar,
        fecha=mesa.fecha.date(),
        examinador=mesa.examinadores.first(),
        examinador_externo=mesa.maestro_invitado,
        observaciones=f"Aprobado en Mesa {mesa.id}. Nota: {inscripcion.nota_tecnica or 'N/A'}. {inscripcion.observaciones}"
    )
