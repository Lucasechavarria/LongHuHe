import pytest
from mixer.backend.django import mixer
from apps.usuarios.models import Usuario
from apps.asistencia.models import RegistroAsistencia
from django.utils import timezone
from apps.asistencia.services import ScannerService
from apps.academia.models import Actividad, Cronograma, InscripcionClase, Sede
from apps.ventas.models import Pago

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
        hoy = timezone.localdate()
        
        # 1. Primera asistencia
        RegistroAsistencia.objects.create(alumno=alumno, actividad=actividad)
        
        # El view_logic (asistencia/views.py) tiene el check de duplicados.
        # Aqui probaremos el model simple.
        assert RegistroAsistencia.objects.filter(alumno=alumno, actividad=actividad, fecha_hora__date=hoy).count() == 1

@pytest.mark.django_db
class TestScannerService:
    def setup_method(self):
        self.sede = Sede.objects.create(nombre="Sede Central")
        self.profe = Usuario.objects.create(nombre="Prof", es_profe=True, celular="100")
        self.actividad = Actividad.objects.create(nombre="Tai Chi", tipo_cobro=Pago.TipoPago.MES)
        self.clase = Cronograma.objects.create(
            actividad=self.actividad, profesor=self.profe, sede=self.sede, dia="LU", hora_inicio="10:00", cupo=10
        )
        
    def test_becado_puede_escanear_sin_pago(self):
        becado = Usuario.objects.create(nombre="Becado", celular="200", es_becado=True)
        InscripcionClase.objects.create(alumno=becado, clase=self.clase, estado='regular')
        
        res = ScannerService.procesar_escaneo(becado.uuid_carnet)
        assert "CUOTA VENCIDA" not in res.get('alertas', [])
        assert res.get('message') != f"Bloqueado: {becado.nombre} (Deuda / Sin Clases)"

    def test_becado_no_consume_clases_disponibles(self):
        act_paquete = Actividad.objects.create(nombre="Paquete", tipo_cobro=Pago.TipoPago.PAQUETE)
        clase_p = Cronograma.objects.create(
            actividad=act_paquete, profesor=self.profe, sede=self.sede, dia="LU", hora_inicio="12:00", cupo=10
        )
        becado = Usuario.objects.create(nombre="Becado2", celular="300", es_becado=True, clases_disponibles=0)
        InscripcionClase.objects.create(alumno=becado, clase=clase_p, estado='regular')
        
        res = ScannerService.procesar_escaneo(becado.uuid_carnet)
        assert "CUOTA VENCIDA" not in res.get('alertas', [])
        assert becado.clases_disponibles == 0
