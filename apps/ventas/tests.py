import pytest
from mixer.backend.django import mixer
from apps.ventas.models import Pago, Pedido, Producto, ProductoVariante, PedidoItem

@pytest.mark.django_db
class TestVentasModel:
    def test_pago_creacion(self):
        monto = 1500
        alumno = mixer.blend('usuarios.Usuario')
        pago = mixer.blend(Pago, alumno=alumno, monto=monto, tipo=Pago.TipoPago.MES)
        assert pago.monto == 1500
        assert pago.estado == Pago.EstadoPago.PENDIENTE

    def test_descuento_stock_pedido(self):
        producto = mixer.blend(Producto, nombre="Gira de Practica", stock=10)
        variante = mixer.blend(ProductoVariante, producto=producto, stock=10)
        
        pedido = mixer.blend(Pedido, estado=Pedido.Estado.PENDIENTE)
        # Necesitamos el Detalle / Item
        mixer.blend(PedidoItem, pedido=pedido, producto=producto, variante=variante, cantidad=2)
        
        # Simular entrega
        pedido.estado = Pedido.Estado.ENTREGADO
        # pedido.descontar_stock()  <-- ELIMINADO: La señal 'actualizar_stock_on_save' ya lo hizo en mixer.blend(PedidoItem)
        
        variante.refresh_from_db()
        assert variante.stock == 8
    
    def test_hay_stock_property(self):
        producto = mixer.blend(Producto, stock=0)
        mixer.blend(ProductoVariante, producto=producto, stock=5)
        assert producto.hay_stock is True
