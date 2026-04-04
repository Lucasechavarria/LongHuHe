from apps.usuarios.models import Usuario

def alumno_context(request):
    """
    Agrega el objeto alumno_actual al contexto global si existe una sesión activa.
    """
    alumno_id = request.session.get('alumno_id')
    if alumno_id:
        try:
            alumno = Usuario.objects.get(id=alumno_id)
            return {'alumno_actual': alumno}
        except Usuario.DoesNotExist:
            return {'alumno_actual': None}
    return {'alumno_actual': None}
