import os
import mercadopago
from .base_gateway import PaymentGatewayStrategy

class MercadoPagoStrategy(PaymentGatewayStrategy):
    """
    Implementación concreta de PaymentGatewayStrategy para Mercado Pago.
    """
    def __init__(self, custom_access_token=None):
        self.access_token = custom_access_token or os.environ.get("MP_ACCESS_TOKEN")
        self.sdk = mercadopago.SDK(self.access_token)

    def crear_preferencia(self, pago):
        base_url = os.environ.get('WEBHOOK_URL_BASE', '')
        if not base_url.startswith('http'):
            print(f"WARNING: WEBHOOK_URL_BASE ('{base_url}') no es una URL absoluta. Las notificaciones de MP fallarán.")
        
        unit_price = float(pago.monto)

        if getattr(pago, 'clase_programada', None):
            dia_abrev = pago.clase_programada.get_dia_display()[:3].upper()
            hora_str = pago.clase_programada.hora_inicio.strftime('%Hhs') if pago.clase_programada.hora_inicio else ""
            titulo_ticket = f"Cuota {dia_abrev} {hora_str} - {pago.clase_programada.actividad.nombre} - Prof. {pago.clase_programada.profesor.nombre_completo}"
        else:
            titulo_ticket = f"Clase de {pago.actividad.nombre} - {pago.get_tipo_display()}"

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
        if "response" in preference_response and "id" in preference_response["response"]:
            preference = preference_response["response"]
            pago.mercado_pago_id = preference["id"]
            # No guardamos el pago aquí para no acoplar la pasarela con el dominio.
            # El llamador debe encargarse de guardarlo.
            return preference.get("init_point"), preference["id"]
        
        print(f"ERROR MP: Respuesta inesperada al crear preferencia: {preference_response}")
        return None, None

    def crear_preferencia_tienda(self, titulo, precio, url_retorno, externo_id):
        base_url = os.environ.get('WEBHOOK_URL_BASE', '')
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
        if "response" in preference_response:
            return preference_response["response"].get("init_point")
        
        print(f"ERROR MP Tienda: {preference_response}")
        return None

    def obtener_pago(self, payment_id):
        payment_info = self.sdk.payment().get(payment_id)
        return payment_info["response"]
