from django.db.models import Count, Sum
from django.db import transaction
from decimal import Decimal
from apps.usuarios.models import Usuario, Grado
from apps.ventas.models import Pago, Pedido
from apps.asistencia.models import RegistroAsistencia
from .models import MesaExamen, InscripcionExamen
import json
from django.core.serializers.json import DjangoJSONEncoder
from datetime import timedelta

class ExamenService:
    """
    Servicio de Dominio para manejar procesos de negocio de Exámenes y Dashboards.
    """

    @staticmethod
    def obtener_metricas_dashboard(hoy):
        """
        Calcula y agrupa todas las métricas globales para el dashboard institucional.
        """
        total_alumnos = Usuario.objects.filter(es_profe=False).count()
        
        # Ingresos mensuales globales (Pagos + Pedidos)
        ingresos_pagos = Pago.objects.filter(
            estado=Pago.EstadoPago.APROBADO, 
            fecha_registro__year=hoy.year,
            fecha_registro__month=hoy.month
        ).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

        ingresos_pedidos = Pedido.objects.filter(
            estado__in=[Pedido.Estado.PAGADO, Pedido.Estado.ENTREGADO],
            fecha_registro__year=hoy.year,
            fecha_registro__month=hoy.month
        ).aggregate(total=Sum('total'))['total'] or Decimal('0.00')

        ingresos_mensuales = ingresos_pagos + ingresos_pedidos
        
        # Asistencia Ultimos 15 Dias
        fecha_limite = hoy - timedelta(days=15)
        asistencias_recientes = RegistroAsistencia.objects.filter(fecha_hora__date__gte=fecha_limite).count()

        # Datos para Graficos (Chart.js)
        grados_qs = Grado.objects.annotate(alumnos_count=Count('alumnos')).order_by('orden')
        grados_data = [
            {'nombre': g.nombre_formateado, 'alumnos_count': g.alumnos_count} 
            for g in grados_qs
        ]
        
        distribucion_grados_json = json.dumps(grados_data, cls=DjangoJSONEncoder)

        alumnos_nuevos_mes = Usuario.objects.filter(
            date_joined__year=hoy.year, 
            date_joined__month=hoy.month
        ).count()
        
        # Exámenes mas recientes
        mesas_abiertas = MesaExamen.objects.filter(esta_abierta=True).annotate(
            candidatos_count=Count('candidatos')
        )

        return {
            'total_alumnos': total_alumnos,
            'ingresos_mensuales': ingresos_mensuales,
            'asistencias_recientes': asistencias_recientes,
            'alumnos_nuevos_mes': alumnos_nuevos_mes,
            'distribucion_grados_json': distribucion_grados_json,
            'mesas_abiertas': mesas_abiertas
        }

    @staticmethod
    @transaction.atomic
    def procesar_evaluaciones(mesa, datos_post):
        """
        Procesa las calificaciones enviadas desde el panel de evaluación.
        Recorre todos los candidatos de la mesa y aplica los cambios y ascensos.
        """
        candidatos = mesa.candidatos.all()
        evaluaciones_procesadas = 0

        for cand in candidatos:
            resultado = datos_post.get(f'resultado_{cand.id}')
            nota = datos_post.get(f'nota_{cand.id}')
            obs = datos_post.get(f'obs_{cand.id}')
            
            if resultado:
                cand.resultado = resultado
                if nota:
                    cand.nota_tecnica = int(nota)
                if obs:
                    cand.observaciones = obs
                cand.save()
                evaluaciones_procesadas += 1
                
        return evaluaciones_procesadas

    @staticmethod
    def inscribir_alumno(mesa, alumno):
        """
        Inscribe a un alumno a una mesa de examen si cumple las condiciones.
        Retorna (inscripcion, error_msg).
        """
        # 1. Verificar Morosidad
        if alumno.estado_morosidad == 'vencido':
            return None, "No puedes inscribirte a exámenes porque tu cuota está vencida. Por favor, regulariza tu situación."

        if InscripcionExamen.objects.filter(mesa=mesa, alumno=alumno).exists():
            return None, "Ya estás inscripto en esta mesa."

        
        # El grado a aspirar es el siguiente al actual
        grado_actual_orden = alumno.grado.orden if alumno.grado else 0
        siguiente_grado = Grado.objects.filter(orden__gt=grado_actual_orden).order_by('orden').first()
        
        if not siguiente_grado:
            return None, "Ya has alcanzado el grado máximo disponible."
            
        inscripcion = InscripcionExamen.objects.create(
            mesa=mesa,
            alumno=alumno,
            grado_a_aspirar=siguiente_grado,
            grado_actual=alumno.grado,
            costo_inscripcion=siguiente_grado.costo_examen + mesa.precio_inscripcion
        )
        
        return inscripcion, None
