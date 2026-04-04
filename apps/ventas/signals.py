from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from datetime import timedelta, date
from .models import Pago, PedidoItem

@receiver(post_save, sender=Pago)
def actualizar_vencimiento_pago(sender, instance, **kwargs):
    if instance.estado == Pago.EstadoPago.APROBADO and instance.tipo == Pago.TipoPago.MES:
        alumno = instance.alumno
        hoy = date.today()
        base_fecha = alumno.fecha_vencimiento_cuota if (alumno.fecha_vencimiento_cuota and alumno.fecha_vencimiento_cuota > hoy) else hoy
        alumno.fecha_vencimiento_cuota = base_fecha + timedelta(days=30)
        alumno.save(update_fields=['fecha_vencimiento_cuota'])

@receiver(post_save, sender=PedidoItem)
def actualizar_stock_on_save(sender, instance, created, **kwargs):
    if created:
        variante = instance.variante
        if variante:
            variante.stock -= instance.cantidad
            variante.save(update_fields=['stock'])

@receiver(post_delete, sender=PedidoItem)
def restaurar_stock_on_delete(sender, instance, **kwargs):
    variante = instance.variante
    if variante:
        variante.stock += instance.cantidad
        variante.save(update_fields=['stock'])
