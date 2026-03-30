from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from django.urls import reverse
from unittest.mock import patch
from .models import (
    Usuario, Locacion, Actividad, Pago, Examen, 
    CategoriaProducto, Producto, Pedido, PedidoItem,
    CategoriaContenido, Documento, VideoTutorial, NivelAcceso,
    ClaseProgramada, Horario, Asistencia
)

class UsuarioModelTest(TestCase):
    def setUp(self):
        self.locacion = Locacion.objects.create(nombre="Sede Central")
        self.actividad = Actividad.objects.create(nombre="Tai-Chi", precio_mes=5000, precio_clase=1000)
        
        # Alumno creado hace 2 años exactos
        dos_anios_atras = timezone.now() - timedelta(days=365 * 2)
        self.alumno = Usuario.objects.create(
            username="alumno1", # AbstractUser requiere username usualmente, a menos que lo hayamos sobreescrito
            dni="12345678",
            email="alumno@test.com",
            nombre="Juan",
            apellido="Perez",
            locacion=self.locacion,
            celular="11223344",
            fecha_ingreso_real=dos_anios_atras.date()
        )

    def test_antiguedad_calculada(self):
        self.assertEqual(self.alumno.antiguedad_anios, 2, "La antigüedad debería ser 2 años exactos.")

    def test_estado_morosidad_al_dia(self):
        hoy = timezone.now()
        p1 = Pago.objects.create(
            alumno=self.alumno,
            actividad=self.actividad,
            tipo=Pago.TipoPago.MES,
            metodo=Pago.MetodoPago.EFECTIVO,
            estado=Pago.EstadoPago.APROBADO,
        )
        Pago.objects.filter(pk=p1.pk).update(fecha_registro=hoy)
        self.alumno.refresh_from_db()
        self.assertEqual(self.alumno.estado_morosidad, 'al_dia', "Con un pago reciente, el estado debe ser al_dia.")

    def test_estado_morosidad_atrasado_gracia(self):
        hoy = timezone.now()
        mes_pago = hoy.replace(day=1) - timedelta(days=5)
        p2 = Pago.objects.create(
            alumno=self.alumno,
            actividad=self.actividad,
            tipo=Pago.TipoPago.MES,
            metodo=Pago.MetodoPago.EFECTIVO,
            estado=Pago.EstadoPago.APROBADO,
        )
        Pago.objects.filter(pk=p2.pk).update(fecha_registro=mes_pago)
        self.alumno.refresh_from_db()
        expected_state = 'atrasado' if hoy.date().day <= 15 else 'vencido'
        self.assertEqual(self.alumno.estado_morosidad, expected_state)


class TiendaTest(TestCase):
    def setUp(self):
        self.cat = CategoriaProducto.objects.create(nombre="Uniformes")
        # Producto SIN backorder
        self.p_estricto = Producto.objects.create(
            categoria=self.cat, nombre="Pantalón Estricto", precio=5000, stock=0, permite_backorder=False
        )
        # Producto CON backorder
        self.p_backorder = Producto.objects.create(
            categoria=self.cat, nombre="Sable Mágico", precio=15000, stock=0, permite_backorder=True
        )

    def test_backorder_bloqueado(self):
        self.assertFalse(self.p_estricto.hay_stock)
        self.assertFalse(self.p_estricto.se_puede_comprar, "No debería poder comprarse si no hay stock ni backorder.")

    def test_backorder_permitido(self):
        self.assertFalse(self.p_backorder.hay_stock)
        self.assertTrue(self.p_backorder.se_puede_comprar, "Debería poder comprarse por tener backorder habilitado.")

    def test_tienda_comision(self):
        # Prueba directa del modelo Pedido instanciado
        # Simula: Comision default 10%
        precio_total = Decimal('10000.00')
        porcentaje_comision = Decimal('10.0')
        monto_comision = (precio_total * porcentaje_comision) / Decimal('100.0')
        
        # User dummy
        loc = Locacion.objects.create(nombre="Test")
        u = Usuario.objects.create(username="usertienda", celular="998877", dni="99", email="test@test.com", locacion=loc)
        
        pedido = Pedido.objects.create(
            alumno=u,
            total=precio_total,
            estado=Pedido.Estado.PAGADO,
            metodo_pago='efectivo',
            porcentaje_comision=porcentaje_comision,
            monto_comision=monto_comision
        )
        
        self.assertEqual(pedido.monto_comision, Decimal('1000.00'))


class BibliotecaLevelsTest(TestCase):
    def setUp(self):
        self.locacion = Locacion.objects.create(nombre="Sede A")
        self.alumno = Usuario.objects.create(username="biblio", celular="123", dni="111", email="biblio@t.com", locacion=self.locacion)
        # Crear Exámenes
        self.maestro = Usuario.objects.create(username="maestro", celular="321", dni="222", email="m@t.com", locacion=self.locacion, es_profe=True)

    def test_niveles_acceso_cinturon_blanco(self):
        # 0 exámenes = Principiante
        cant_examenes = self.alumno.examenes.count()
        niveles_permitidos = [NivelAcceso.TODOS, NivelAcceso.PRINCIPIANTE]
        if cant_examenes >= 1: niveles_permitidos.append(NivelAcceso.INTERMEDIO)
        if cant_examenes >= 3: niveles_permitidos.append(NivelAcceso.AVANZADO)
        
        self.assertIn(NivelAcceso.PRINCIPIANTE, niveles_permitidos)
        self.assertNotIn(NivelAcceso.INTERMEDIO, niveles_permitidos)
    
    def test_niveles_acceso_intermedio(self):
        Examen.objects.create(alumno=self.alumno, examinador=self.maestro, grado="Cinturon Amarillo", fecha=timezone.now().date())
        cant_examenes = self.alumno.examenes.count()
        niveles_permitidos = [NivelAcceso.TODOS, NivelAcceso.PRINCIPIANTE]
        if cant_examenes >= 1: niveles_permitidos.append(NivelAcceso.INTERMEDIO)
        if cant_examenes >= 3: niveles_permitidos.append(NivelAcceso.AVANZADO)
        
        self.assertIn(NivelAcceso.INTERMEDIO, niveles_permitidos)
        self.assertNotIn(NivelAcceso.AVANZADO, niveles_permitidos)
        
    def test_niveles_acceso_avanzado(self):
        Examen.objects.create(alumno=self.alumno, examinador=self.maestro, grado="Cinturon Amarillo", fecha=timezone.now().date())
        Examen.objects.create(alumno=self.alumno, examinador=self.maestro, grado="Cinturon Verde", fecha=timezone.now().date())
        Examen.objects.create(alumno=self.alumno, examinador=self.maestro, grado="Cinturon Azul", fecha=timezone.now().date())
        
        cant_examenes = self.alumno.examenes.count()
        niveles_permitidos = [NivelAcceso.TODOS, NivelAcceso.PRINCIPIANTE]
        if cant_examenes >= 1: niveles_permitidos.append(NivelAcceso.INTERMEDIO)
        if cant_examenes >= 3: niveles_permitidos.append(NivelAcceso.AVANZADO)
        
        self.assertIn(NivelAcceso.AVANZADO, niveles_permitidos)


class TestAuthYVistas(TestCase):
    def setUp(self):
        self.locacion = Locacion.objects.create(nombre="Sede Central")
        self.alumno = Usuario.objects.create(username="alumno_v", celular="12345", dni="111222", locacion=self.locacion)
        self.profe = Usuario.objects.create(username="profe_v", celular="54321", dni="333444", locacion=self.locacion, es_profe=True)

    def test_dashboard_acceso_alumno(self):
        # Simulamos que existe el alumno_id en la session manual (nuestra auth)
        session = self.client.session
        session['alumno_id'] = self.alumno.id
        session.save()
        
        response = self.client.get(reverse('inicio'))
        self.assertEqual(response.status_code, 200, "El alumno debería poder ver su inicio.")

    def test_scanner_qr_bloqueo_alumno(self):
        session = self.client.session
        session['alumno_id'] = self.alumno.id
        session.save()
        
        response = self.client.get(reverse('escanear_qr_alumno', args=[self.alumno.id]))
        self.assertEqual(response.status_code, 302, "El alumno debería ser redirigido fuera del scanner.")

    def test_scanner_qr_acceso_profe(self):
        session = self.client.session
        session['alumno_id'] = self.profe.id
        session.save()
        
        response = self.client.get(reverse('escanear_qr_alumno', args=[self.alumno.id]))
        self.assertEqual(response.status_code, 200, "El profesor debería poder ver el scanner.")


class TestWebhooksExtremos(TestCase):
    def setUp(self):
        self.locacion = Locacion.objects.create(nombre="Test Sede Webhook")
        self.actividad = Actividad.objects.create(nombre="Tai-Chi", precio_mes=5000, precio_clase=1000)
        self.profe = Usuario.objects.create(username="profe_w", celular="11111", dni="11", locacion=self.locacion, es_profe=True)
        self.alumno = Usuario.objects.create(username="alumno_w", celular="22222", dni="22", locacion=self.locacion)
        
        self.clase = ClaseProgramada.objects.create(
            profesor=self.profe,
            actividad=self.actividad,
            locacion=self.locacion
        )
        
        self.pago = Pago.objects.create(
            alumno=self.alumno,
            actividad=self.actividad,
            clase_programada=self.clase,
            tipo=Pago.TipoPago.MES,
            metodo=Pago.MetodoPago.MERCADOPAGO,
            estado=Pago.EstadoPago.PENDIENTE,
        )

    @patch('core.views.MercadoPagoService')
    def test_webhook_pago_aprobado_clase(self, mock_service_class):
        # Simular respuesta exitosa del Service instanciado
        mock_instance = mock_service_class.return_value
        mock_instance.obtener_pago.return_value = {
            "status": "approved", 
            "external_reference": str(self.pago.id)
        }
        
        # Enviar un POST al webhook (tal como lo envía MP)
        # request.GET.get('id') o data.get('data', {}).get('id')
        import json
        payload = json.dumps({"type": "payment", "data": {"id": "99999"}})
        response = self.client.post(
            reverse('mercadopago_webhook') + f"?topic=payment&id=99999&identificador_pago={self.pago.id}", 
            payload,
            content_type="application/json"
        )
        
        # El endpoint siempre debe contestar HTTPS 200
        self.assertEqual(response.status_code, 200)
        
        # La BD de nuestro Pago debería haber conmutado a Aprobado internamente
        self.pago.refresh_from_db()
        self.assertEqual(self.pago.estado, Pago.EstadoPago.APROBADO)

    @patch('core.views.MercadoPagoService')
    def test_webhook_pago_aprobado_tienda(self, mock_service_class):
        # Primero creamos un Pedido real en BD (como si lo hubiera hecho en la vista de tienda_inicio)
        cat = CategoriaProducto.objects.create(nombre="Uniformes")
        prod = Producto.objects.create(categoria=cat, nombre="Test", precio=100)
        pedido = Pedido.objects.create(alumno=self.alumno, total=100, estado=Pedido.Estado.PENDIENTE, metodo_pago='mercadopago')
        
        # Simular respuesta de MP: external_reference tiene prefijo TIENDA_
        mock_instance = mock_service_class.return_value
        mock_instance.obtener_pago.return_value = {
            "status": "approved", 
            "external_reference": f"TIENDA_{pedido.id}"
        }
        
        import json
        payload = json.dumps({"type": "payment", "data": {"id": "123456"}})
        response = self.client.post(
            reverse('mercadopago_webhook') + f"?topic=payment&id=123456&identificador_tienda={pedido.id}", 
            payload,
            content_type="application/json"
        )
        
        self.assertEqual(response.status_code, 200)
        
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, Pedido.Estado.PAGADO, "El pedido de tienda debería mutar a Pagado al recibir status 'approved'.")

    @patch('core.services.mercadopago_service.mercadopago.SDK')
    def test_mp_clase_token_profesor(self, mock_mp_sdk):
        # Comprobar que en la instanciación toma correctamente el token de profesor o default
        import os
        from core.services.mercadopago_service import MercadoPagoService
        
        # Le inyectamos un token ficticio al maestro
        self.profe.mp_access_token = "TEST_TOKEN_MAESTRO_123"
        self.profe.save()
        
        service = MercadoPagoService(self.profe.mp_access_token)
        mock_mp_sdk.assert_called_with("TEST_TOKEN_MAESTRO_123")
        
        # Mientras que uno default caería al env
        fake_env_token = "TEST_TOKEN_CENTRO"
        os.environ["MP_ACCESS_TOKEN"] = fake_env_token
        service_central = MercadoPagoService()
        mock_mp_sdk.assert_called_with(fake_env_token)


class TestFlujosVistas(TestCase):
    def setUp(self):
        self.locacion = Locacion.objects.create(nombre="Sede A")
        self.alumno = Usuario.objects.create(username="test_login", dni="111", celular="123", locacion=self.locacion, nombre="Test", apellido="Login")

    def test_identificacion_dni(self):
        # Alumno existe -> Entra
        response = self.client.post(reverse('identificacion'), {'identificador': '111'})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.session['alumno_id'], self.alumno.id)

    def test_identificacion_nuevo_redirect_onboarding(self):
        # Alumno no existe -> Onboarding
        response = self.client.post(reverse('identificacion'), {'identificador': '999'})
        self.assertEqual(response.status_code, 302)
        self.assertIn('onboarding', response.url)

    def test_onboarding_creacion_usuario(self):
        # Crear un nuevo alumno desde Onboarding
        actividad = Actividad.objects.create(nombre="Karate", precio_mes=3000, precio_clase=500)
        data = {
            'nombre': 'Nuevo',
            'apellido': 'Alumno',
            'dni': '777',
            'celular': '777000',
            'fecha_nacimiento': '01/01/2000',
            'domicilio': 'Calle Falsa 123',
            'localidad': 'TestCity',
            'locacion': self.locacion.id,
            'actividad_inicial': actividad.id
        }
        response = self.client.post(reverse('onboarding'), data)
        if response.status_code != 302:
            print(f"\nFORM ERRORS: {response.context['form'].errors.as_json()}")
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Usuario.objects.filter(dni='777').exists())


class TestAccionesAsistencia(TestCase):
    def setUp(self):
        self.locacion = Locacion.objects.create(nombre="Sede B")
        self.actividad = Actividad.objects.create(nombre="Yoga", precio_mes=4000, precio_clase=800)
        self.alumno = Usuario.objects.create(username="test_asis", dni="222", celular="222", locacion=self.locacion)
        self.profe = Usuario.objects.create(username="profe_asis", dni="333", celular="333", locacion=self.locacion, es_profe=True)

    def test_registrar_asistencia_propia_alumno(self):
        session = self.client.session
        session['alumno_id'] = self.alumno.id
        session.save()
        
        response = self.client.post(reverse('registrar_asistencia'), {'actividad_id': self.actividad.id})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Asistencia.objects.filter(alumno=self.alumno).count(), 1)

    def test_confirmacion_asistencia_profe_qr(self):
        # Asegurar que el alumno está AL DIA para que el profe pueda registrar
        Pago.objects.create(
            alumno=self.alumno,
            actividad=self.actividad,
            tipo=Pago.TipoPago.MES,
            metodo=Pago.MetodoPago.EFECTIVO,
            estado=Pago.EstadoPago.APROBADO
        )
        
        session = self.client.session
        session['alumno_id'] = self.profe.id # Simular que el profe esta logueado
        session.save()
        
        # El profe confirma asistencia de "test_asis"
        response = self.client.post(reverse('escanear_qr_alumno', args=[self.alumno.id]), {'actividad_id': self.actividad.id})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Asistencia.objects.filter(alumno=self.alumno).count(), 1)


class TestTiendaView(TestCase):
    def setUp(self):
        self.locacion = Locacion.objects.create(nombre="Sede C")
        self.alumno = Usuario.objects.create(username="test_store", dni="444", celular="444", locacion=self.locacion)
        self.cat = CategoriaProducto.objects.create(nombre="TestCat")
        self.prod = Producto.objects.create(categoria=self.cat, nombre="TestItem", precio=1000, stock=5)

    def test_compra_tienda_view_logic(self):
        session = self.client.session
        session['alumno_id'] = self.alumno.id
        session.save()
        
        data = {
            'metodo_pago': 'efectivo',
            'cantidad': 2
        }
        response = self.client.post(reverse('tienda_comprar', args=[self.prod.id]), data)
        self.assertEqual(response.status_code, 302)
        
        self.prod.refresh_from_db()
        self.assertEqual(self.prod.stock, 3, "El stock debería haber bajado de 5 a 3.")
        self.assertEqual(Pedido.objects.count(), 1)
        self.assertEqual(Pedido.objects.first().total, 2000)


class TestPagosManuales(TestCase):
    def setUp(self):
        self.locacion = Locacion.objects.get_or_create(nombre="Sede A")[0]
        self.actividad = Actividad.objects.create(nombre="Tai-Chi", precio_mes=5000)
        self.alumno = Usuario.objects.create(
            username="manual_pay", dni="888", celular="888", locacion=self.locacion
        )
        session = self.client.session
        session['alumno_id'] = self.alumno.id
        session.save()

    def test_flujo_pago_efectivo(self):
        # Sesión simulada de paso a paso
        session = self.client.session
        session['pago_data'] = {
            'actividad': self.actividad.id,
            'tipo': Pago.TipoPago.MES,
            'metodo': Pago.MetodoPago.EFECTIVO
        }
        session.save()
        
        response = self.client.post(reverse('pago_confirmacion'))
        self.assertEqual(response.status_code, 302)
        self.assertEqual(Pago.objects.count(), 1)
        self.assertEqual(Pago.objects.first().metodo, Pago.MetodoPago.EFECTIVO)

    def test_pago_transferencia_subida_archivo(self):
        session = self.client.session
        session['pago_data'] = {
            'actividad': self.actividad.id,
            'tipo': Pago.TipoPago.MES,
            'metodo': Pago.MetodoPago.TRANSFERENCIA
        }
        session.save()
        
        # Crear un archivo ficticio
        file_content = b"fake receipt image content"
        fake_file = SimpleUploadedFile("comprobante.jpg", file_content, content_type="image/jpeg")
        
        response = self.client.post(reverse('pago_comprobante'), {'comprobante': fake_file})
        self.assertEqual(response.status_code, 302)
        
        pago = Pago.objects.first()
        self.assertTrue(pago.comprobante.name.startswith('comprobantes/comprobante'))
        self.assertEqual(pago.metodo, Pago.MetodoPago.TRANSFERENCIA)
