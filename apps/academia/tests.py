import pytest
from mixer.backend.django import mixer
from apps.academia.models import Sede, Actividad, Cronograma, InscripcionClase

@pytest.mark.django_db
class TestAcademiaModel:
    def test_sede_creacion(self):
        sede = mixer.blend(Sede, nombre="Sede Norte")
        assert str(sede) == "Sede Norte"

    def test_actividad_precio(self):
        actividad = mixer.blend(Actividad, nombre="Tai-Chi", precio_mes=5000)
        assert actividad.precio_mes == 5000

    def test_cronograma_relacion(self):
        profe = mixer.blend('usuarios.Usuario', es_profe=True)
        sede = mixer.blend(Sede)
        actividad = mixer.blend(Actividad)
        clase = mixer.blend(Cronograma, profesor=profe, sede=sede, actividad=actividad)
        
        assert clase.profesor == profe
        assert str(clase).startswith(actividad.nombre)

    def test_cupo_maximo(self):
        clase = mixer.blend(Cronograma, cupo=2)
        mixer.blend(InscripcionClase, clase=clase)
        mixer.blend(InscripcionClase, clase=clase)
        # 3era inscripcion? 
        # (Actualmente no tenemos validacion de error en el SAVE, pero lo probaremos)
        assert clase.alumnos_inscritos.count() == 2
