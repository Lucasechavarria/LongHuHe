import pytest
from mixer.backend.django import mixer
from apps.usuarios.models import Usuario, Grado
from django.utils import timezone
from datetime import timedelta

@pytest.mark.django_db
class TestUsuarioModel:
    def test_usuario_creacion(self):
        # Usamos None en username para forzar la lógica de auto-generación en save()
        usuario = mixer.blend(Usuario, nombre="Juan", apellido="Perez", celular="123456789", username=None)
        assert usuario.nombre_completo == "Juan Perez"
        assert usuario.username == "123456789"

    def test_alerta_inasistencia_nueva(self):
        # Alumno nuevo sin asistencias -> True (Alerta)
        alumno = mixer.blend(Usuario)
        assert alumno.alerta_inasistencia is True

    def test_alerta_inasistencia_antigua(self, db):
        from apps.asistencia.models import RegistroAsistencia
        alumno = mixer.blend(Usuario)
        # Hace 20 dias
        fecha_vieja = timezone.now() - timedelta(days=20)
        asistencia = mixer.blend(RegistroAsistencia, alumno=alumno)
        asistencia.fecha_hora = fecha_vieja
        asistencia.save()
        
        assert alumno.alerta_inasistencia is True

    def test_alerta_inasistencia_reciente(self, db):
        from apps.asistencia.models import RegistroAsistencia
        alumno = mixer.blend(Usuario)
        mixer.blend(RegistroAsistencia, alumno=alumno, fecha_hora=timezone.now())
        assert alumno.alerta_inasistencia is False

    def test_estado_morosidad_sin_pagos(self):
        alumno = mixer.blend(Usuario, fecha_vencimiento_cuota=None)
        # Sin pagos y sin fecha -> Vencido
        assert alumno.estado_morosidad == "vencido"

    def test_estado_morosidad_al_dia(self):
        vencimiento = timezone.now().date() + timedelta(days=10)
        alumno = mixer.blend(Usuario, fecha_vencimiento_cuota=vencimiento)
        assert alumno.estado_morosidad == "al_dia"

    def test_generar_qr(self):
        alumno = mixer.blend(Usuario)
        qr_base64 = alumno.generar_qr_base64
        assert qr_base64.startswith("data:image/png;base64,")

@pytest.mark.django_db
class TestGradoModel:
    def test_grado_jerarquia(self):
        g1 = mixer.blend(Grado, nombre="Blanco", orden=0)
        g2 = mixer.blend(Grado, nombre="Amarillo", orden=1)
        assert g1.orden < g2.orden
        assert str(g1) == "Blanco"
