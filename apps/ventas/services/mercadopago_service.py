import mercadopago
import os
class MercadoPagoService:
    def __init__(self, custom_access_token=None):
        self.access_token = custom_access_token or os.environ.get("MP_ACCESS_TOKEN")
        self.sdk = mercadopago.SDK(self.access_token)

    def crear_preferencia(self, pago):
        """
        Crea una preferencia de pago en Mercado Pago basada en un objeto Pago.
        """
        from apps.ventas.models import Pago # Importación absoluta para evitar fallos
        
        # ✅ Validación de Webhook: Mercado Pago requiere una URL ABSOLUTA
        base_url = os.environ.get('WEBHOOK_URL_BASE', '')
        if not base_url.startswith('http'):
            # En producción esto sería un error crítico
            print(f"WARNING: WEBHOOK_URL_BASE ('{base_url}') no es una URL absoluta. Las notificaciones de MP fallarán.")
        
        # ✅ BUG FIX: Usar el monto final calculado en el ERP (con descuentos)
        unit_price = float(pago.monto)

        # Generación del título descriptivo del ticket ("Triangulación Perfecta")
        if pago.clase_programada:
            dia_abrev = pago.clase_programada.get_dia_display()[:3].upper()
            hora_str = pago.clase_programada.hora_inicio.strftime('%Hhs') if pago.clase_programada.hora_inicio else ""
            
            titulo_ticket = f"Cuota {dia_abrev} {hora_str} - {pago.clase_programada.actividad.nombre} - Prof. {pago.clase_programada.profesor.nombre_completo}"
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
