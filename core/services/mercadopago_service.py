import mercadopago
import os
from django.conf import settings
class MercadoPagoService:
    def __init__(self):
        self.access_token = os.environ.get("MP_ACCESS_TOKEN")
        self.sdk = mercadopago.SDK(self.access_token)

    def crear_preferencia(self, pago):
        """
        Crea una preferencia de pago en Mercado Pago basada en un objeto Pago.
        Retorna el init_point para redirigir al usuario.
        """
        from .models import Pago # Importar aquí para evitar circularidad
        # Calcular el monto basado en el tipo de pago
        unit_price = 0
        if pago.tipo == Pago.TipoPago.MES:
            unit_price = float(pago.actividad.precio_mes)
        elif pago.tipo == Pago.TipoPago.CLASE_SUELTA:
            unit_price = float(pago.actividad.precio_clase)
        elif pago.tipo == Pago.TipoPago.PAQUETE:
            # Si es paquete, podríamos calcular precio_clase * cantidad_clases
            unit_price = float(pago.actividad.precio_clase) * (pago.cantidad_clases or 1)

        preference_data = {
            "items": [
                {
                    "title": f"Clase de {pago.actividad.nombre} - {pago.get_tipo_display()}",
                    "quantity": 1,
                    "unit_price": unit_price,
                    "currency_id": "ARS"
                }
            ],
            "payer": {
                "email": pago.alumno.email or "alumno@longhuhe.com.ar",
                "name": pago.alumno.nombre,
                "surname": pago.alumno.apellido
            },
            "back_urls": {
                "success": f"{os.environ.get('WEBHOOK_URL_BASE')}/gracias/",
                "failure": f"{os.environ.get('WEBHOOK_URL_BASE')}/pago-tipo/",
                "pending": f"{os.environ.get('WEBHOOK_URL_BASE')}/gracias/"
            },
            "auto_return": "approved",
            "notification_url": f"{os.environ.get('WEBHOOK_URL_BASE')}/mercadopago/webhook/",
            "external_reference": str(pago.id)
        }

        preference_response = self.sdk.preference().create(preference_data)
        preference = preference_response["response"]
        
        # Guardamos el ID de la preferencia para rastreo
        pago.mercado_pago_id = preference["id"]
        pago.save()

        return preference["init_point"]

    def obtener_pago(self, payment_id):
        """
        Consulta el estado de un pago específico en la API de Mercado Pago.
        """
        payment_info = self.sdk.payment().get(payment_id)
        return payment_info["response"]
