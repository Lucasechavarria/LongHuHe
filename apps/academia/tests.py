from django.test import TestCase
from apps.usuarios.models import Usuario
from apps.academia.models import Actividad, Cronograma, InscripcionClase, Sede
from apps.academia.services import AcademiaService
from apps.ventas.models import Pago
from datetime import date, timedelta

class AcademiaServiceTest(TestCase):
    def setUp(self):
        self.profe = Usuario.objects.create(nombre="P", es_profe=True)
        self.actividad = Actividad.objects.create(nombre="T", tipo_cobro="mes")
        self.actividad_paquete = Actividad.objects.create(nombre="TP", tipo_cobro="paquete")
        self.sede = Sede.objects.create(nombre="Sede")
        self.clase = Cronograma.objects.create(
            actividad=self.actividad, profesor=self.profe, sede=self.sede,
            dia="LU", hora_inicio="10:00", cupo=2
        )
        # Alumno al día por defecto
        self.alumno = Usuario.objects.create(
            nombre="A", celular="123", 
            fecha_vencimiento_cuota=date.today() + timedelta(days=10)
        )

    def test_inscribir_alumno_respeta_cupo(self):
        """ Verificar que el 3er alumno entre en lista de espera si el cupo es 2 """
        a1 = Usuario.objects.create(nombre="A1", celular="1", fecha_vencimiento_cuota=date.today() + timedelta(days=10))
        a2 = Usuario.objects.create(nombre="A2", celular="2", fecha_vencimiento_cuota=date.today() + timedelta(days=10))
        a3 = Usuario.objects.create(nombre="A3", celular="3", fecha_vencimiento_cuota=date.today() + timedelta(days=10))
        
        AcademiaService.inscribir_alumno(a1, self.clase.id)
        AcademiaService.inscribir_alumno(a2, self.clase.id)
        insc3, msg, ok = AcademiaService.inscribir_alumno(a3, self.clase.id)
        
        self.assertIsNotNone(insc3, f"Error en inscripción: {msg}")
        self.assertEqual(insc3.estado, InscripcionClase.EstadoInscrito.ESPERA)

    def test_dar_de_baja_promueve_espera(self):
        """ Si un REGULAR se da de baja, el primero en ESPERA debe subir """
        a1 = Usuario.objects.create(nombre="A1", celular="1", fecha_vencimiento_cuota=date.today() + timedelta(days=10))
        a2 = Usuario.objects.create(nombre="A2", celular="2", fecha_vencimiento_cuota=date.today() + timedelta(days=10))
        a3 = Usuario.objects.create(nombre="A3", celular="3", fecha_vencimiento_cuota=date.today() + timedelta(days=10))
        
        AcademiaService.inscribir_alumno(a1, self.clase.id)
        AcademiaService.inscribir_alumno(a2, self.clase.id)
        AcademiaService.inscribir_alumno(a3, self.clase.id) # En espera
        
        # Baja del a1
        AcademiaService.dar_de_baja(a1, self.clase.id)
        
        # a3 ahora debe ser REGULAR
        insc3 = InscripcionClase.objects.get(alumno=a3, clase=self.clase)
        self.assertEqual(insc3.estado, InscripcionClase.EstadoInscrito.REGULAR)

    def test_inscribir_paquete_descuenta_saldo(self):
        """ Al inscribirse en REGULAR de un paquete, debe descontar 1 clase """
        clase_p = Cronograma.objects.create(
            actividad=self.actividad_paquete, profesor=self.profe, sede=self.sede,
            dia="MA", hora_inicio="10:00", cupo=10
        )
        self.alumno.clases_disponibles = 5
        self.alumno.save()
        
        insc, msg, ok = AcademiaService.inscribir_alumno(self.alumno, clase_p.id)
        self.assertTrue(ok)
        
        self.alumno.refresh_from_db()
        self.assertEqual(self.alumno.clases_disponibles, 4)

    def test_dar_de_baja_reintegra_saldo_paquete(self):
        """ Al darse de baja de un paquete siendo REGULAR, debe devolver el crédito """
        clase_p = Cronograma.objects.create(
            actividad=self.actividad_paquete, profesor=self.profe, sede=self.sede,
            dia="MI", hora_inicio="10:00", cupo=10
        )
        self.alumno.clases_disponibles = 5
        self.alumno.save()
        
        AcademiaService.inscribir_alumno(self.alumno, clase_p.id)
        self.alumno.refresh_from_db()
        self.assertEqual(self.alumno.clases_disponibles, 4)
        
        # Baja
        AcademiaService.dar_de_baja(self.alumno, clase_p.id)
        self.alumno.refresh_from_db()
        self.assertEqual(self.alumno.clases_disponibles, 5)

    def test_promocion_espera_valida_saldo_paquete(self):
        """ Un alumno en espera solo es promovido si tiene saldo (paquetes) """
        clase_p = Cronograma.objects.create(
            actividad=self.actividad_paquete, profesor=self.profe, sede=self.sede,
            dia="JU", hora_inicio="10:00", cupo=1
        )
        
        # A1 ocupa el único lugar
        a1 = Usuario.objects.create(nombre="A1", celular="1", clases_disponibles=1, fecha_vencimiento_cuota=date.today())
        AcademiaService.inscribir_alumno(a1, clase_p.id)
        
        # A2 entra en espera (con 1 clase)
        a2 = Usuario.objects.create(nombre="A2", celular="2", clases_disponibles=1, fecha_vencimiento_cuota=date.today())
        AcademiaService.inscribir_alumno(a2, clase_p.id)
        
        # A3 entra en espera (con 1 clase, luego se la quitamos)
        a3 = Usuario.objects.create(nombre="A3", celular="3", clases_disponibles=1, fecha_vencimiento_cuota=date.today())
        AcademiaService.inscribir_alumno(a3, clase_p.id)
        a3.clases_disponibles = 0
        a3.save()
        
        # Baja de A1
        AcademiaService.dar_de_baja(a1, clase_p.id)
        
        # A2 debe ser promovido y su saldo debe ser 0
        insc2 = InscripcionClase.objects.get(alumno=a2, clase=clase_p)
        a2.refresh_from_db()
        self.assertEqual(insc2.estado, InscripcionClase.EstadoInscrito.REGULAR)
        self.assertEqual(a2.clases_disponibles, 0)
        
        # A3 debe seguir en espera
        insc3 = InscripcionClase.objects.get(alumno=a3, clase=clase_p)
        self.assertEqual(insc3.estado, InscripcionClase.EstadoInscrito.ESPERA)
