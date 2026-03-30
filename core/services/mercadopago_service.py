import mercadopago
import os
from django.conf import settings
class MercadoPagoService:
    def __init__(self, custom_access_token=None):
        self.access_token = custom_access_token or os.environ.get("MP_ACCESS_TOKEN")
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

        # Generación del título descriptivo del ticket ("Triangulación Perfecta")
        if pago.clase_programada:
            dias_abrev = "-".join([h.get_dia_display()[:3].upper() for h in pago.clase_programada.horarios.all()])
            hs_inicio = pago.clase_programada.horarios.first()
            hora_str = hs_inicio.hora_inicio.strftime('%Hhs') if hs_inicio else ""
            
            titulo_ticket = f"Cuota {dias_abrev} {hora_str} - {pago.clase_programada.actividad.nombre} - Prof. {pago.clase_programada.profesor.nombre_completo}"
        else:
            titulo_ticket = f"Clase de {pago.actividad.nombre} - {pago.get_tipo_display()}"

        # URL del webhook con parámetro identificador para rutear la credencial
        base_url = os.environ.get('WEBHOOK_URL_BASE', '')
        webhook_url = f"{base_url}/mercadopago/webhook/?identificador_pago={pago.id}"

        preference_data = {
            "items": [
                {
                    "title": titulo_ticket,
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
                "success": f"{base_url}/gracias/",
                "failure": f"{base_url}/pago-tipo/",
                "pending": f"{base_url}/gracias/"
            },
            "auto_return": "approved",
            "notification_url": webhook_url,
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

    def crear_preferencia_tienda(self, titulo, precio, url_retorno, externo_id):
        """
        Crea una preferencia directa para carrito de compras / tienda.
        """
        base_url = os.environ.get('WEBHOOK_URL_BASE', '')
        # En la tienda, el dinero va a la central (por defecto SIN access_token sobreescrito)
        webhook_url = f"{base_url}/mercadopago/webhook/?identificador_tienda={externo_id}"

        preference_data = {
            "items": [
                {
                    "title": titulo,
                    "quantity": 1,
                    "unit_price": precio,
                    "currency_id": "ARS"
                }
            ],
            "back_urls": {
                "success": url_retorno,
                "failure": url_retorno,
                "pending": url_retorno
            },
            "auto_return": "approved",
            "notification_url": webhook_url,
            "external_reference": str(externo_id)
        }

        preference_response = self.sdk.preference().create(preference_data)
        preference = preference_response["response"]
        return preference["init_point"]
