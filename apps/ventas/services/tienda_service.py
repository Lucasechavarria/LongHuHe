from decimal import Decimal
from django.db import transaction
from django.shortcuts import get_object_or_404
from apps.ventas.models import Pedido, PedidoItem, Producto, ProductoVariante

class TiendaService:
    @staticmethod
    @transaction.atomic
    def crear_pedido_desde_carrito(alumno, carrito_data, metodo):
        """
        Procesa el carrito y genera el pedido, asegurando el bloqueo de stock.
        """
        if not carrito_data:
            raise ValueError("El carrito está vacío.")

        pedido = Pedido.objects.create(
            alumno=alumno,
            estado=Pedido.Estado.PENDIENTE,
            metodo_pago=metodo
        )

        total_gral = Decimal('0.0')
        tiene_backorder = False

        for doc in carrito_data:
            prod = get_object_or_404(Producto.objects.select_for_update(), id=doc['id'])
            var = None
            qty_raw = doc.get('qty', 1)
            try:
                qty = int(qty_raw)
            except (ValueError, TypeError):
                qty = 1
            
            if doc.get('variant_id'):
                var = get_object_or_404(ProductoVariante.objects.select_for_update(), id=doc.get('variant_id'))
                if var.stock < qty:
                    if not prod.permite_backorder:
                        transaction.set_rollback(True)
                        raise ValueError(f"¡Error! Por milisegundos alguien más se llevó lo último de {prod.nombre} ({var.talle}).")
                    else:
                        tiene_backorder = True
            elif prod.stock < qty:
                if not prod.permite_backorder:
                    transaction.set_rollback(True)
                    raise ValueError(f"¡Error! Por milisegundos alguien más se llevó lo último de {prod.nombre}.")
                else:
                    tiene_backorder = True
            
            precio_unitario = prod.precio if prod.precio else Decimal('0.00')
            item_total = precio_unitario * qty
            total_gral += item_total
            
            PedidoItem.objects.create(
                pedido=pedido,
                producto=prod,
                variante=var,
                cantidad=qty,
                precio_unitario=prod.precio
            )
        
        pedido.total = total_gral
        pedido.backorder = tiene_backorder
        pedido.save() # Dispara el recalcular_stats de models.py

        return pedido

    @staticmethod
    @transaction.atomic
    def crear_pedido_directo(alumno, producto_id, cantidad, metodo_pago):
        """
        Crea un pedido directamente para un único producto (usado en tienda_comprar).
        Retorna (pedido, error_msg)
        """
        producto = get_object_or_404(Producto.objects.select_for_update(), id=producto_id)
        
        if not producto.hay_stock and not producto.permite_backorder:
            return None, "Stock insuficiente."

        precio_total = producto.precio * cantidad
        
        # Buscar profesor venta (primera clase)
        from apps.ventas.models import Pago
        profesor_venta = None
        primera_clase = Pago.objects.filter(alumno=alumno, clase_programada__isnull=False).order_by('-fecha_registro').first()
        if primera_clase and primera_clase.clase_programada:
            profesor_venta = primera_clase.clase_programada.profesor
            
        porcentaje_comision = producto.porcentaje_comision if profesor_venta else Decimal('0.0')
        monto_comision = (precio_total * porcentaje_comision) / Decimal('100.0')
        
        es_backorder = False if producto.hay_stock else True

        pedido = Pedido.objects.create(
            alumno=alumno, total=precio_total, metodo_pago=metodo_pago,
            estado=Pedido.Estado.PENDIENTE, profesor_venta=profesor_venta,
            porcentaje_comision=porcentaje_comision, monto_comision=monto_comision,
            backorder=es_backorder
        )
        
        PedidoItem.objects.create(
            pedido=pedido, producto=producto, cantidad=cantidad, precio_unitario=producto.precio
        )

        return pedido, None
