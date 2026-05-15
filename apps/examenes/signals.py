from django.dispatch import Signal

# Señal disparada cuando un alumno aprueba un examen y asciende de grado.
# kwargs enviados: inscripcion
ascenso_aprobado = Signal()
