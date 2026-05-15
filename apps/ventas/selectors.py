from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from decimal import Decimal
from apps.ventas.models import Pago, Pedido

class TesoreriaSelector:
    @staticmethod
    def obtener_kpis_mes(mes, anio):
        pagos_aprobados_mes = Pago.objects.filter(
            estado=Pago.EstadoPago.APROBADO, 
            fecha_registro__month=mes,
            fecha_registro__year=anio
        )
        pedidos_pagados_mes = Pedido.objects.filter(
            estado__in=[Pedido.Estado.PAGADO, Pedido.Estado.ENTREGADO],
            fecha_registro__month=mes,
            fecha_registro__year=anio
        )
        
        ingresos_pagos = pagos_aprobados_mes.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
        ingresos_pedidos = pedidos_pagados_mes.aggregate(total=Sum('total'))['total'] or Decimal('0.00')
        
        return {
            'ingresos_pagos': ingresos_pagos,
            'ingresos_pedidos': ingresos_pedidos,
            'ingresos_totales': ingresos_pagos + ingresos_pedidos
        }

    @staticmethod
    def obtener_tendencia_diaria(dias=30):
        tendencia_data = Pago.objects.filter(
            estado=Pago.EstadoPago.APROBADO,
            fecha_registro__gte=timezone.now() - timedelta(days=dias)
        ).annotate(date=TruncDate('fecha_registro')).values('date').annotate(
            total=Sum('monto')
        ).order_by('date')
        
        return {
            'labels': [d['date'].strftime("%d/%m") for d in tendencia_data],
            'values': [float(d['total']) for d in tendencia_data]
        }

    @staticmethod
    def obtener_distribucion_metodos():
        metodos_data = Pago.objects.filter(estado=Pago.EstadoPago.APROBADO).values('metodo').annotate(count=Count('id'))
        return {
            'labels': [dict(Pago.MetodoPago.choices).get(d['metodo'], d['metodo']) for d in metodos_data],
            'values': [d['count'] for d in metodos_data]
        }
    
    @staticmethod
    def obtener_ingresos_por_actividad(mes, anio):
        qs = Pago.objects.filter(
            estado=Pago.EstadoPago.APROBADO,
            fecha_registro__month=mes,
            fecha_registro__year=anio
        ).values('actividad__nombre').annotate(total=Sum('monto'))
        
        resultado = []
        for item in qs:
            nombre = item['actividad__nombre'] or "Otros (Exámenes/Varios)"
            resultado.append({'nombre': nombre, 'total': item['total']})
        return resultado

    @staticmethod
    def obtener_ingresos_por_tipo(mes, anio):
        qs = Pago.objects.filter(
            estado=Pago.EstadoPago.APROBADO,
            fecha_registro__month=mes,
            fecha_registro__year=anio
        ).values('tipo').annotate(total=Sum('monto'))
        
        stats_tipos = {
            'mes': Decimal('0.00'),
            'clase_suelta': Decimal('0.00'),
            'paquete': Decimal('0.00'),
            'examen': Decimal('0.00'),
        }
        for item in qs:
            stats_tipos[item['tipo']] = item['total']
        return stats_tipos
