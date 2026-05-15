from apps.usuarios.models import Usuario

class UsuarioSessionMiddleware:
    """
    Middleware que inyecta el objeto Usuario (user_obj) en el request
    basado en el ID almacenado en la sesión personalizada del ERP.
    Esto evita múltiples consultas repetitivas en decoradores y vistas.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Intentar obtener el ID de la sesión personalizada
        alumno_id = request.session.get('alumno_id')
        
        request.user_obj = None
        
        if alumno_id:
            # Usamos filter().first() para evitar excepciones y manejar IDs inválidos
            request.user_obj = Usuario.objects.filter(id=alumno_id).first()
        
        # 2. Si no hay sesión personalizada pero sí auth de Django (Admin/Staff)
        if not request.user_obj and request.user.is_authenticated:
            # Aseguramos que sea un objeto de nuestro modelo Usuario
            if isinstance(request.user, Usuario):
                request.user_obj = request.user
            else:
                request.user_obj = Usuario.objects.filter(id=request.user.id).first()

        response = self.get_response(request)
        return response
