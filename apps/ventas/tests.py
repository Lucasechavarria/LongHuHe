from django.test import TestCase
from django.utils import timezone
from apps.usuarios.models import Usuario
from apps.academia.models import Actividad, Sede, Cronograma
from .models import Pago, Pedido, Producto, CategoriaProducto
from .services.pago_service import PagoService
from .services.tienda_service import TiendaService
from .services.pedido_service import PedidoService
from decimal import Decimal

class PagoServiceTest(TestCase):
    def setUp(self):
        self.profe = Usuario.objects.create(
            nombre="Profe", apellido="Test", celular="12345", es_profe=True,
            mp_access_token="test_token"
        )
        self.alumno = Usuario.objects.create(
            nombre="Alumno", apellido="Test", celular="67890", es_profe=False,
            fecha_vencimiento_cuota=timezone.now().date() + timezone.timedelta(days=30)
        )
        self.actividad = Actividad.objects.create(
            nombre="Tai Chi", precio_mes=5000, precio_clase=1000, tipo_cobro="mes"
        )
        self.sede = Sede.objects.create(nombre="Sede Central")
        self.clase = Cronograma.objects.create(
            actividad=self.actividad, profesor=self.profe, sede=self.sede,
            dia="LU", hora_inicio="10:00"
        )

    def test_registrar_pago_mes_calcula_comision(self):
        """ Verificar que al registrar un pago de mes, se calcule la comisión (default 50%) """
        pago = PagoService.registrar_pago(
            alumno=self.alumno,
            actividad=self.actividad,
            tipo=Pago.TipoPago.MES,
            metodo=Pago.MetodoPago.EFECTIVO
        )
        pago.clase_programada = self.clase
        pago.save()
        
        PagoService.recalcular_comisiones(pago)
        
        # Default es 50%
        self.assertEqual(pago.monto_comision_profesor, Decimal('2500.00')) 

class TiendaServiceTest(TestCase):
    def setUp(self):
        self.alumno = Usuario.objects.create(nombre="A", apellido="B", celular="1")
        self.cat = CategoriaProducto.objects.create(nombre="Ropa")
        self.producto = Producto.objects.create(
            categoria=self.cat, nombre="Remera", precio=2000, stock=10, activo=True
        )

    def test_crear_pedido_valida_stock(self):
        """ No se puede crear un pedido si no hay stock suficiente """
        items = [{'id': self.producto.id, 'qty': 15}]
        
        with self.assertRaises(ValueError) as cm:
            TiendaService.crear_pedido_desde_carrito(self.alumno, items, metodo='efectivo')
        
        self.assertIn("llevó lo último", str(cm.exception))

    def test_crear_pedido_descuenta_stock_al_pagar(self):
        """ El stock debe descontarse solo cuando el pedido se marca como pagado """
        items = [{'id': self.producto.id, 'qty': 2}]
        pedido = TiendaService.crear_pedido_desde_carrito(self.alumno, items, metodo='efectivo')
        
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)
        
        PedidoService.transicionar_a_pagado(pedido)
        
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 8)

    def test_cancelar_pedido_restaura_stock(self):
        """ Si un pedido pagado se cancela, el stock debe devolverse """
        items = [{'id': self.producto.id, 'qty': 3}]
        pedido = TiendaService.crear_pedido_desde_carrito(self.alumno, items, metodo='efectivo')
        
        PedidoService.transicionar_a_pagado(pedido)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 7)
        
        PedidoService.transicionar_a_cancelado(pedido)
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.stock, 10)
