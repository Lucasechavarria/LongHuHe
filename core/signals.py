from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from datetime import timedelta, date
from .models import Pago, PedidoItem, Producto

@receiver(post_save, sender=Pago)
def actualizar_vencimiento_pago(sender, instance, **kwargs):
    """
    Cuando un pago de cuota mensual es aprobado, actualiza la fecha de vencimiento del alumno.
    Suma 30 días a la fecha actual o a la fecha de vencimiento anterior (si no ha vencido).
    """
    if instance.estado == Pago.EstadoPago.APROBADO and instance.tipo == Pago.TipoPago.MES:
        alumno = instance.alumno
        hoy = date.today()
        
        # Si ya tiene un vencimiento futuro, le sumamos a ese. 
        # Si no tiene o ya venció, le sumamos a hoy.
        base_fecha = alumno.fecha_vencimiento_cuota if (alumno.fecha_vencimiento_cuota and alumno.fecha_vencimiento_cuota > hoy) else hoy
        
        alumno.fecha_vencimiento_cuota = base_fecha + timedelta(days=30)
        alumno.save(update_fields=['fecha_vencimiento_cuota'])


@receiver(post_save, sender=PedidoItem)
def actualizar_stock_on_save(sender, instance, created, **kwargs):
    """
    Resta stock del producto cuando se crea un PedidoItem.
    """
    if created:
        producto = instance.producto
        producto.stock -= instance.cantidad
        producto.save(update_fields=['stock'])


@receiver(post_delete, sender=PedidoItem)
def restaurar_stock_on_delete(sender, instance, **kwargs):
    """
    Restaura el stock si se elimina un item del pedido (ej. cancelación manual).
    """
    producto = instance.producto
    producto.stock += instance.cantidad
    producto.save(update_fields=['stock'])
