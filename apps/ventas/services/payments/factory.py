from .mercadopago_strategy import MercadoPagoStrategy

class PaymentGatewayFactory:
    """
    Fábrica para obtener la pasarela de pagos configurada.
    Actualmente devuelve siempre MercadoPagoStrategy, pero permite
    extensión a futuro (ej. leyendo configuraciones desde DB o settings).
    """
    @staticmethod
    def get_gateway(gateway_name="mercadopago", custom_access_token=None):
        if gateway_name.lower() == "mercadopago":
            return MercadoPagoStrategy(custom_access_token)
        else:
            raise ValueError(f"Pasarela '{gateway_name}' no soportada.")
