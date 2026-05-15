from decimal import Decimal, ROUND_HALF_UP
from django.db import transaction, models


class PedidoService:
    """
    Servicio de Dominio para manejar el ciclo de vida y la máquina de estados de Pedido.
    """

    @staticmethod
    def descontar_stock(pedido):
        """ Reduce el inventario al entregar o pagar el producto """
        if pedido.stock_descontado:
            return
        
        for item in pedido.items.all():
            if item.variante:
                item.variante.stock = models.F('stock') - item.cantidad
                item.variante.save(update_fields=['stock'])
            else:
                item.producto.stock = models.F('stock') - item.cantidad
                item.producto.save(update_fields=['stock'])
        
        pedido.stock_descontado = True
        pedido.save(update_fields=['stock_descontado'])

    @staticmethod
    def restaurar_stock(pedido):
        """ Devuelve el inventario si se cancela un pedido """
        if not pedido.stock_descontado:
            return
            
        for item in pedido.items.all():
            if item.variante:
                item.variante.stock = models.F('stock') + item.cantidad
                item.variante.save(update_fields=['stock'])
            else:
                item.producto.stock = models.F('stock') + item.cantidad
                item.producto.save(update_fields=['stock'])
        
        pedido.stock_descontado = False
        pedido.save(update_fields=['stock_descontado'])

    @staticmethod
    def recalcular_stats(pedido):
        """ Recalcula costos de reposición y utilidad basándose en los items actuales. """
        if getattr(pedido, 'estado', None) in ["pagado", "reservado", "entregado"]:
            total_costo = Decimal('0.00')
            for item in pedido.items.all():
                costo_item = (Decimal(str(item.producto.costo_reposicion)) * item.cantidad)
                total_costo += costo_item
            
            pedido.monto_costo_reposicion = total_costo.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            pct_comision = Decimal(str(pedido.porcentaje_comision)) / Decimal('100')
            pedido.monto_comision = (pedido.total * pct_comision).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            if pedido.clase_origen and pedido.clase_origen.profesor_asistente:
                pct_asistente = Decimal(str(pedido.clase_origen.porcentaje_comision_asistente)) / Decimal('100')
                pedido.monto_comision_asistente = (pedido.total * pct_asistente).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            else:
                pedido.monto_comision_asistente = Decimal('0.00')
            
            pedido.utilidad_neta_asociacion = (
                pedido.total - pedido.monto_costo_reposicion - 
                pedido.monto_comision - pedido.monto_comision_asistente
            ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            pedido.save(update_fields=[
                'monto_costo_reposicion', 'monto_comision', 
                'monto_comision_asistente', 'utilidad_neta_asociacion'
            ])

    @staticmethod
    @transaction.atomic
    def transicionar_a_pagado(pedido):
        pedido.estado = "pagado" # Pedido.Estado.PAGADO
        PedidoService.descontar_stock(pedido)
        PedidoService.recalcular_stats(pedido)
        pedido.save()

    @staticmethod
    @transaction.atomic
    def transicionar_a_entregado(pedido):
        pedido.estado = "entregado" # Pedido.Estado.ENTREGADO
        PedidoService.descontar_stock(pedido)
        PedidoService.recalcular_stats(pedido)
        pedido.save()

    @staticmethod
    @transaction.atomic
    def transicionar_a_cancelado(pedido):
        pedido.estado = "cancelado" # Pedido.Estado.CANCELADO
        PedidoService.restaurar_stock(pedido)
        pedido.save()
