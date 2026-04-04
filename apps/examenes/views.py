from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta
from apps.usuarios.views import profe_requerido
from apps.usuarios.models import Usuario, Grado
from apps.asistencia.models import RegistroAsistencia
from apps.ventas.models import Pago
from .models import MesaExamen, InscripcionExamen
from django.contrib import messages

import json
from django.core.serializers.json import DjangoJSONEncoder

@profe_requerido
def dashboard_institucional(request):
    """ Task 7.4: Dashboards Globales """
    hoy = timezone.now().date()
    # Estadisticas basicas
    total_alumnos = Usuario.objects.filter(es_profe=False).count()
    ingresos_mensuales = Pago.objects.filter(
        estado=Pago.EstadoPago.APROBADO, 
        fecha_registro__month=hoy.month
    ).aggregate(Sum('monto'))['monto__sum'] or 0
    
    # Asistencia Ultimos 15 Dias
    fecha_limite = hoy - timedelta(days=15)
    asistencias_recientes = RegistroAsistencia.objects.filter(fecha_hora__date__gte=fecha_limite).count()

    # Datos para Graficos (Chart.js Task 7.5)
    grados_data = list(Grado.objects.annotate(
        alumnos_count=Count('usuario')
    ).values('nombre', 'alumnos_count').order_by('orden'))
    
    distribucion_grados_json = json.dumps(grados_data, cls=DjangoJSONEncoder)

    alumnos_nuevos_mes = Usuario.objects.filter(date_joined__month=hoy.month).count()
    
    # Exámenes mas recientes
    mesas_abiertas = MesaExamen.objects.filter(esta_abierta=True).annotate(
        candidatos_count=Count('candidatos')
    )

    return render(request, 'examenes/dashboard.html', {
        'total_alumnos': total_alumnos,
        'ingresos_mensuales': ingresos_mensuales,
        'asistencias_recientes': asistencias_recientes,
        'alumnos_nuevos_mes': alumnos_nuevos_mes,
        'distribucion_grados_json': distribucion_grados_json,
        'mesas_abiertas': mesas_abiertas
    })

@profe_requerido
def evaluar_mesa(request, mesa_id):
    """ Task 7.2: Panel de evaluación """
    mesa = get_object_or_404(MesaExamen, id=mesa_id)
    candidatos = mesa.candidatos.all().select_related('alumno', 'grado_a_aspirar')
    
    if request.method == 'POST':
        # Procesamiento masivo de resultados
        for cand in candidatos:
            resultado = request.POST.get(f'resultado_{cand.id}')
            nota = request.POST.get(f'nota_{cand.id}')
            obs = request.POST.get(f'obs_{cand.id}')
            
            if resultado:
                cand.resultado = resultado
                if nota:
                    cand.nota_tecnica = int(nota)
                if obs:
                    cand.observaciones = obs
                cand.save()
                
                # Ejecutar ascenso si aprobó (Task 7.3)
                if resultado == InscripcionExamen.EstadoResultado.APROBADO:
                    cand.aplicar_ascenso()
                    
        messages.success(request, f"Mesa {mesa.id} evaluada correctamente.")
        return redirect('dashboard_institucional')

    return render(request, 'examenes/evaluar_mesa.html', {
        'mesa': mesa,
        'candidatos': candidatos,
        'resultados_opciones': InscripcionExamen.EstadoResultado.choices
    })
