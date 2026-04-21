from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta
from apps.usuarios.views import profe_requerido, alumno_requerido
from apps.usuarios.models import Usuario, Grado
from decimal import Decimal
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
    from apps.ventas.models import Pedido
    
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

    # Datos para Graficos (Chart.js Task 7.5)
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



@alumno_requerido
def inscribir_examen(request, mesa_id):
    """ Permite al alumno inscribirse a una mesa abierta. """
    mesa = get_object_or_404(MesaExamen, id=mesa_id, esta_abierta=True)
    alumno = request.user_obj
    
    if InscripcionExamen.objects.filter(mesa=mesa, alumno=alumno).exists():
        messages.warning(request, "Ya estás inscripto en esta mesa.")
        return redirect('perfil')
    
    # El grado a aspirar es el siguiente al actual
    grado_actual_orden = alumno.grado.orden if alumno.grado else 0
    siguiente_grado = Grado.objects.filter(orden__gt=grado_actual_orden).order_by('orden').first()
    
    if not siguiente_grado:
        messages.info(request, "Ya has alcanzado el grado máximo disponible.")
        return redirect('perfil')
        
    InscripcionExamen.objects.create(
        mesa=mesa,
        alumno=alumno,
        grado_a_aspirar=siguiente_grado,
        grado_actual=alumno.grado,
        costo_inscripcion=siguiente_grado.costo_examen + mesa.precio_inscripcion
    )
    
    messages.success(request, f"Inscripción exitosa para el grado: {siguiente_grado.nombre}. Ahora procede al pago.")
    return redirect('pago_examen', mesa_id=mesa.id)

@alumno_requerido
def pago_examen(request, mesa_id):
    """ Task 12.3: Selección de método de pago para el examen. """
    mesa = get_object_or_404(MesaExamen, id=mesa_id)
    inscripcion = get_object_or_404(InscripcionExamen, mesa=mesa, alumno=request.user_obj)
    
    if request.method == 'POST':
        metodo = request.POST.get('metodo')
        if not metodo:
            messages.error(request, "Debes seleccionar un método de pago.")
        else:
            # Creamos el objeto Pago similar a la tienda
            pago = Pago.objects.create(
                alumno=request.user_obj,
                monto=inscripcion.costo_inscripcion,
                metodo=metodo,
                tipo=Pago.TipoPago.EXAMEN,
                estado=Pago.EstadoPago.PENDIENTE
            )
            inscripcion.pago = pago
            inscripcion.save()
            
            if metodo == Pago.MetodoPago.MERCADOPAGO:
                return redirect('pago_mercadopago_checkout', pago_id=pago.id)
            elif metodo == Pago.MetodoPago.TRANSFERENCIA:
                return redirect('pago_comprobante_examen', pago_id=pago.id)
            else: # Efectivo
                messages.success(request, "Pedido de examen registrado. Deberás abonar en efectivo al profesor para confirmar.")
                return redirect('perfil')

    return render(request, 'examenes/pago_examen.html', {
        'mesa': mesa,
        'inscripcion': inscripcion
    })

@alumno_requerido
def pago_comprobante_examen(request, pago_id):
    """ Sube el comprobante de transferencia para el examen. """
    pago = get_object_or_404(Pago, id=pago_id, alumno=request.user_obj)
    from apps.ventas.forms import PagoComprobanteForm
    
    if request.method == 'POST':
        form = PagoComprobanteForm(request.POST, request.FILES, instance=pago)
        if form.is_valid():
            form.save()
            messages.success(request, "Comprobante enviado. El administrador verificará tu pago.")
            return redirect('perfil')
    else:
        form = PagoComprobanteForm(instance=pago)
        
    return render(request, 'examenes/pago_comprobante.html', {'form': form, 'pago': pago})
