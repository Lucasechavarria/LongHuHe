from abc import ABC, abstractmethod

class PaymentGatewayStrategy(ABC):
    """
    Interfaz abstracta para todas las pasarelas de pago del ERP.
    Garantiza que cualquier proveedor futuro (PayPal, Stripe) exponga
    exactamente estos métodos requeridos por el sistema.
    """
    
    @abstractmethod
    def crear_preferencia(self, pago):
        """
        Genera el ticket o intención de cobro para una cuota o clase.
        Debe devolver la URL (init_point) adonde se redirigirá al usuario.
        """
        pass

    @abstractmethod
    def crear_preferencia_tienda(self, titulo, precio, url_retorno, externo_id):
        """
        Genera el ticket de cobro explícitamente para el carrito de compras.
        Debe devolver la URL de pago.
        """
        pass

    @abstractmethod
    def obtener_pago(self, payment_id):
        """
        Consulta la API externa para obtener el estado real de un pago.
        Retorna un diccionario estandarizado o el payload original validable.
        """
        pass
