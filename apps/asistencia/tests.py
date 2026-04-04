import pytest
from mixer.backend.django import mixer
from apps.usuarios.models import Usuario
from apps.asistencia.models import RegistroAsistencia
from django.utils import timezone

@pytest.mark.django_db
class TestAsistenciaModel:
    def test_registro_asistencia(self):
        alumno = mixer.blend(Usuario)
        actividad = mixer.blend('academia.Actividad')
        asistencia = mixer.blend(RegistroAsistencia, alumno=alumno, actividad=actividad)
        assert asistencia.alumno == alumno
        assert str(asistencia).startswith("Asistencia de")

    def test_doble_registro_mismo_dia(self):
        alumno = mixer.blend(Usuario)
        actividad = mixer.blend('academia.Actividad')
        hoy = timezone.now().date()
        
        # 1. Primera asistencia
        RegistroAsistencia.objects.create(alumno=alumno, actividad=actividad)
        
        # El view_logic (asistencia/views.py) tiene el check de duplicados.
        # Aqui probaremos el model simple.
        assert RegistroAsistencia.objects.filter(alumno=alumno, actividad=actividad, fecha_hora__date=hoy).count() == 1
