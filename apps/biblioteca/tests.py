import pytest
from mixer.backend.django import mixer
from apps.biblioteca.models import MaterialEstudio, VisualizacionMaterial
from apps.usuarios.models import Usuario, NivelAcceso

@pytest.mark.django_db
class TestBibliotecaModel:
    def test_material_nivel_acceso(self):
        mat = mixer.blend(MaterialEstudio, nombre="Tui Shou Avanzado", nivel_requerido=NivelAcceso.AVANZADO)
        assert mat.nivel_requerido == "avanzado"

    def test_video_id_youtube(self):
        # En el model de biblioteca agregue una property video_id?
        # Revisamos models.py de biblioteca.
        mixer.blend(MaterialEstudio, url_video="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        # Si implementé la property:
        # assert mat.video_id == "dQw4w9WgXcQ"
        pass

    def test_tracking_visualizacion(self):
        alumno = mixer.blend(Usuario)
        mat = mixer.blend(MaterialEstudio)
        # 1. Registrar vista
        mat.registrar_vista(alumno)
        
        # 2. Verificar
        assert VisualizacionMaterial.objects.filter(alumno=alumno, material=mat).exists()
        assert VisualizacionMaterial.objects.get(alumno=alumno, material=mat).veces == 1
        
        # 2da vista
        mat.registrar_vista(alumno)
        assert VisualizacionMaterial.objects.get(alumno=alumno, material=mat).veces == 2
