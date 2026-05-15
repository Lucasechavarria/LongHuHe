from django.shortcuts import render, get_object_or_404, redirect

from django.utils import timezone
from apps.usuarios.views import profe_requerido, alumno_requerido
from apps.ventas.models import Pago
from .models import MesaExamen, InscripcionExamen
from django.contrib import messages



@profe_requerido
def dashboard_institucional(request):
    """ Task 7.4: Dashboards Globales """
    hoy = timezone.now().date()
    from apps.examenes.services import ExamenService
    
    metricas = ExamenService.obtener_metricas_dashboard(hoy)

    return render(request, 'examenes/dashboard.html', metricas)

@profe_requerido
def evaluar_mesa(request, mesa_id):
    """ Task 7.2: Panel de evaluación """
    mesa = get_object_or_404(MesaExamen, id=mesa_id)
    candidatos = mesa.candidatos.all().select_related('alumno', 'grado_a_aspirar')
    
    if request.method == 'POST':
        from apps.examenes.services import ExamenService
        evaluaciones_procesadas = ExamenService.procesar_evaluaciones(mesa, request.POST)
        
        messages.success(request, f"Mesa {mesa.id} evaluada. {evaluaciones_procesadas} candidatos procesados.")
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
    
    from apps.examenes.services import ExamenService
    inscripcion, error_msg = ExamenService.inscribir_alumno(mesa, alumno)
    
    if error_msg:
        messages.warning(request, error_msg)
        return redirect('perfil')
    
    messages.success(request, f"Inscripción exitosa para el grado: {inscripcion.grado_a_aspirar.nombre}. Ahora procede al pago.")
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
