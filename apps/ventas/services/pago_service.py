from decimal import Decimal
from django.db import transaction, models
from datetime import date
import calendar
from apps.ventas.models import Descuento

class PagoService:
    """
    Servicio de Dominio para manejar la lógica de estado de los Pagos (State Machine Pattern).
    Evita los "Fat Models" y side-effects automáticos en el método save().
    """

    @staticmethod
    @transaction.atomic
    def registrar_pago(alumno, actividad, tipo, metodo, comprobante=None, cantidad_clases=None, descuento_id=None):
        """
        Crea un nuevo registro de pago inicial.
        """
        from apps.ventas.models import Pago
        pago = Pago.objects.create(
            alumno=alumno,
            actividad=actividad,
            tipo=tipo,
            metodo=metodo,
            comprobante=comprobante,
            cantidad_clases=cantidad_clases,
            descuento_id=descuento_id,
            estado=Pago.EstadoPago.PENDIENTE
        )
        return pago


    @staticmethod
    def recalcular_comisiones(pago):
        """ Calcula cuánto va para el profe y cuánto para la asociación. """
        if not pago.monto:
            return
        
        pct = Decimal('50.00') # Default base: 50%
        
        if pago.clase_programada:
            pct = pago.clase_programada.porcentaje_comision_profesor
        elif pago.actividad and hasattr(pago.actividad, 'porcentaje_comision'):
            pct = pago.actividad.porcentaje_comision
        
        pago.monto_comision_profesor = (pago.monto * (pct / Decimal('100'))).quantize(Decimal('0.01'))
        pago.monto_utilidad_asociacion = pago.monto - pago.monto_comision_profesor

    @staticmethod
    @transaction.atomic
    def transicionar_a_aprobado(pago):
        """
        Ejecuta la transición al estado APROBADO.
        Incluye cálculos de comisiones, consumo de cupones y auto-renovación de cuotas.
        """
        if pago.estado == pago.EstadoPago.APROBADO:
            return # Ya estaba aprobado

        pago.estado = pago.EstadoPago.APROBADO

        # 1. Calcular comisiones del profesor
        if pago.monto_comision_profesor == 0:
            PagoService.recalcular_comisiones(pago)

        # 2. Incrementar contador de usos del descuento
        if pago.descuento_id and pago.tipo == pago.TipoPago.MES:
            Descuento.objects.filter(pk=pago.descuento_id).update(
                usos_actuales=models.F('usos_actuales') + 1
            )

        # 3. Lógica de Vencimiento Cíclico
        hoy = date.today()
        alumno = pago.alumno

        if pago.tipo == pago.TipoPago.MES:
            if not alumno.dia_corte_cuota:
                alumno.dia_corte_cuota = hoy.day

            dia_corte = alumno.dia_corte_cuota
            base = alumno.fecha_vencimiento_cuota if (alumno.fecha_vencimiento_cuota and alumno.fecha_vencimiento_cuota >= hoy) else hoy
            mes_sig = base.month % 12 + 1
            anio_sig = base.year + (1 if base.month == 12 else 0)

            ultimo_dia_mes_sig = calendar.monthrange(anio_sig, mes_sig)[1]
            dia_real = min(dia_corte, ultimo_dia_mes_sig)

            nuevo_vencimiento = date(anio_sig, mes_sig, dia_real)

            alumno.fecha_vencimiento_cuota = nuevo_vencimiento
            alumno.fecha_prorroga = None
            alumno.save(update_fields=['fecha_vencimiento_cuota', 'fecha_prorroga', 'dia_corte_cuota'])

        elif pago.tipo in [pago.TipoPago.PAQUETE, pago.TipoPago.CLASE_SUELTA]:
            clases_a_sumar = pago.cantidad_clases or (1 if pago.tipo == pago.TipoPago.CLASE_SUELTA else 0)
            alumno.clases_disponibles = models.F('clases_disponibles') + clases_a_sumar
            alumno.save(update_fields=['clases_disponibles'])

        pago.save()
