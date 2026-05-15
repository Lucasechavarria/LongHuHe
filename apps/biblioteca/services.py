from .models import MaterialEstudio, VisualizacionMaterial

class BibliotecaService:
    """
    Servicio encargado de la lógica de acceso y tracking de la biblioteca.
    """

    @staticmethod
    def obtener_materiales_para_alumno(alumno):
        """
        Retorna los materiales habilitados según el grado del alumno.
        """
        grado_alumno = alumno.grado
        if not grado_alumno:
            return MaterialEstudio.objects.none()
            
        return MaterialEstudio.objects.filter(
            grado_minimo__orden__lte=grado_alumno.orden,
            activo=True
        ).select_related('categoria', 'grado_minimo')

    @staticmethod
    def registrar_visualizacion(alumno, material):
        """
        Registra o incrementa el contador de visualizaciones.
        """
        VisualizacionMaterial.registrar_vista(
            alumno=alumno,
            material=material
        )
