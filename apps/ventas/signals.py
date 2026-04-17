from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import PedidoItem

# NOTA: El signal `actualizar_vencimiento_pago` fue ELIMINADO intencionalmente.
# La lógica de vencimiento de cuota vive únicamente en Pago.save()
# para evitar la doble actualización que causaba vencimientos incorrectos.

@receiver(post_delete, sender=PedidoItem)
def restaurar_stock_on_delete(sender, instance, **kwargs):
    """Restaura el stock de la variante si se elimina un item de pedido."""
    variante = instance.variante
    if variante:
        variante.stock += instance.cantidad
        variante.save(update_fields=['stock'])
