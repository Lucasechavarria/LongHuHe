from django.db import models
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Usuario, Asistencia, Pago, Locacion, Actividad
from .forms import AlumnoOnboardingForm, PagoTipoForm, PagoMetodoForm, PagoComprobanteForm
from .services.mercadopago_service import MercadoPagoService # Importar el servicio
from functools import wraps
from django.views.decorators.csrf import csrf_exempt # Para el webhook
import json

def alumno_requerido(view_func):
    """
    Decorador para asegurar que el alumno está identificado en la sesión.
    Si no, lo manda al onboarding.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if 'alumno_id' not in request.session:
            return redirect('onboarding')
        
        # Opcional: Verificar que el usuario aún exista
        if not Usuario.objects.filter(id=request.session['alumno_id']).exists():
            del request.session['alumno_id']
            return redirect('onboarding')
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def splash(request):
    """
    Pantalla de inicio premium con el logo 3D.
    """
    if 'alumno_id' in request.session:
        return redirect('inicio')
    return render(request, 'core/splash.html')


def acceso_opciones(request):
    """
    Pantalla intermedia para elegir entre loguearse como alumno existente
    o iniciar el proceso de inscripción.
    """
    if 'alumno_id' in request.session:
        return redirect('inicio')
    return render(request, 'core/acceso_opciones.html')


def identificacion(request):
    """
    Paso de identificación mediante DNI o Celular para alumnos existentes.
    Si no se encuentra el alumno, se le redirige al onboarding para que se inscriba.
    """
    if 'alumno_id' in request.session:
        return redirect('inicio')

    if request.method == 'POST':
        identificador = request.POST.get('identificador', '').strip()
        if identificador:
            # Buscamos por celular o DNI
            alumno = Usuario.objects.filter(Q(celular__icontains=identificador) | Q(dni=identificador)).first()
            
            if alumno:
                request.session['alumno_id'] = alumno.id
                messages.success(request, f"¡Bienvenido nuevamente, {alumno.nombre}!")
                return redirect('inicio')
            else:
                # No se encontró, lo enviamos a inscribirse (onboarding)
                messages.info(request, "No encontramos tus datos. ¡Por favor, completa tu inscripción!")
                return redirect('onboarding')

    return render(request, 'core/identificacion.html')


def onboarding(request):
    """
    Paso inicial para que el alumno se identifique.
    """
    if 'alumno_id' in request.session:
        return redirect('inicio')

    if request.method == 'POST':
        form = AlumnoOnboardingForm(request.POST)
        if form.is_valid():
            # Buscamos por celular o DNI para no duplicar
            celular = form.cleaned_data['celular']
            dni = form.cleaned_data['dni']
            
            usuario, created = Usuario.objects.get_or_create(
                celular=celular,
                defaults={
                    'nombre': form.cleaned_data['nombre'],
                    'apellido': form.cleaned_data['apellido'],
                    'dni': dni,
                    'fecha_nacimiento': form.cleaned_data['fecha_nacimiento'],
                    'domicilio': form.cleaned_data['domicilio'],
                    'localidad': form.cleaned_data['localidad'],
                    'locacion': form.cleaned_data['locacion'],
                    'username': f"user_{celular}", # Username técnico
                }
            )
            
            # Si ya existía, actualizamos los datos
            if not created:
                usuario.nombre = form.cleaned_data['nombre']
                usuario.apellido = form.cleaned_data['apellido']
                usuario.dni = dni
                usuario.fecha_nacimiento = form.cleaned_data['fecha_nacimiento']
                usuario.domicilio = form.cleaned_data['domicilio']
                usuario.localidad = form.cleaned_data['localidad']
                usuario.locacion = form.cleaned_data['locacion']
                usuario.save()

            # Agregamos la actividad seleccionada (MTOM)
            actividad = form.cleaned_data.get('actividad_inicial')
            if actividad:
                usuario.actividades.add(actividad)
                
            request.session['alumno_id'] = usuario.id
            return redirect('inicio')
    else:
        form = AlumnoOnboardingForm()
    
    return render(request, 'core/onboarding.html', {'form': form})


@alumno_requerido
def inicio(request):
    """
    Pantalla principal con los CTAs gigantes.
    """
    alumno = Usuario.objects.get(id=request.session['alumno_id'])
    locaciones = Locacion.objects.prefetch_related('actividades').all()
    return render(request, 'core/inicio.html', {
        'alumno': alumno,
        'locaciones': locaciones
    })


@alumno_requerido
def registrar_asistencia(request):
    """
    Registra la asistencia y redirige a gracias.
    Espera 'actividad_id' en el POST.
    """
    if request.method == 'POST':
        alumno = Usuario.objects.get(id=request.session['alumno_id'])
        actividad_id = request.POST.get('actividad_id')
        actividad = get_object_or_404(Actividad, id=actividad_id)
        Asistencia.objects.create(alumno=alumno, actividad=actividad)
        messages.success(request, f"¡Asistencia a {actividad.nombre} registrada!")
        return redirect('gracias')
    return redirect('inicio')


@alumno_requerido
def pago_tipo(request):
    """
    Paso 1 del pago.
    """
    if request.method == 'POST':
        # ¿Viene del modal con todos los datos integrados?
        if 'metodo' in request.POST:
            form_tipo = PagoTipoForm(request.POST)
            form_metodo = PagoMetodoForm(request.POST)
            if form_tipo.is_valid() and form_metodo.is_valid():
                alumno = Usuario.objects.get(id=request.session['alumno_id'])
                Pago.objects.create(
                    alumno=alumno,
                    actividad=form_tipo.cleaned_data['actividad'],
                    tipo=form_tipo.cleaned_data['tipo'],
                    cantidad_clases=form_tipo.cleaned_data.get('cantidad_clases'),
                    metodo=form_metodo.cleaned_data['metodo'],
                    comprobante=request.FILES.get('comprobante')
                )
                if 'pago_data' in request.session:
                    del request.session['pago_data']
                return redirect('gracias')

        # Flujo tradicional paso a paso
        form = PagoTipoForm(request.POST)
        if form.is_valid():
            pago_data = form.cleaned_data
            if 'actividad' in pago_data and hasattr(pago_data['actividad'], 'id'):
                pago_data['actividad'] = pago_data['actividad'].id
            request.session['pago_data'] = pago_data
            request.session.modified = True
            return redirect('pago_metodo')
    else:
        form = PagoTipoForm()
    
    return render(request, 'core/pago_tipo.html', {'form': form})


@alumno_requerido
def pago_metodo(request):
    """
    Paso 2 del pago.
    """
    if 'pago_data' not in request.session:
        return redirect('pago_tipo')

    if request.method == 'POST':
        form = PagoMetodoForm(request.POST)
        if form.is_valid():
            pago_data = request.session['pago_data']
            pago_data.update(form.cleaned_data)
            request.session['pago_data'] = pago_data
            request.session.modified = True
            
            # Si es efectivo o Mercado Pago, terminamos aquí o vamos a confirmación
            if form.cleaned_data['metodo'] in [Pago.MetodoPago.EFECTIVO, Pago.MetodoPago.MERCADOPAGO]:
                return redirect('pago_confirmacion')
            
            return redirect('pago_comprobante')
    else:
        form = PagoMetodoForm()
    
    return render(request, 'core/pago_metodo.html', {'form': form})


@alumno_requerido
def pago_comprobante(request):
    """
    Paso 3: Subida de comprobante.
    """
    if 'pago_data' not in request.session:
        return redirect('pago_tipo')

    if request.method == 'POST':
        form = PagoComprobanteForm(request.POST, request.FILES)
        if form.is_valid():
            # Guardamos el archivo en un lugar temporal o esperamos al final?
            # En Django es mejor guardarlo al crear el objeto.
            # Pasamos el archivo a la siguiente vista a través de la sesión? 
            # Sesión no aguanta FILES fácilmente. 
            # Guardamos el Pago aquí y adjuntamos el archivo.
            
            alumno = Usuario.objects.get(id=request.session['alumno_id'])
            pago_data = request.session['pago_data']
            
            # Obtenemos el objeto Actividad desde el ID guardado
            actividad_id = pago_data['actividad']
            if hasattr(actividad_id, 'id'): activity_obj = actividad_id
            else: activity_obj = get_object_or_404(Actividad, id=actividad_id)
            
            pago = Pago.objects.create(
                alumno=alumno,
                actividad=activity_obj,
                tipo=pago_data['tipo'],
                cantidad_clases=pago_data.get('cantidad_clases'),
                metodo=pago_data.get('metodo') or pago_data.get('método'),
                comprobante=request.FILES.get('comprobante')
            )
            
            # Si el método es Mercado Pago, redirigimos al checkout automático
            if pago.metodo == Pago.MetodoPago.MERCADOPAGO:
                return redirect('pago_mercadopago_checkout', pago_id=pago.id)

            del request.session['pago_data']
            return redirect('gracias')
    else:
        form = PagoComprobanteForm()
    
    return render(request, 'core/pago_comprobante.html', {'form': form})


@alumno_requerido
def pago_confirmacion(request):
    """
    Confirmación final para pagos en efectivo (donde no hay comprobante).
    """
    if 'pago_data' not in request.session:
        return redirect('pago_tipo')

    alumno = Usuario.objects.get(id=request.session['alumno_id'])
    pago_data = request.session['pago_data']
    
    # Obtenemos la actividad para el context y para crear el objeto
    actividad_id = pago_data['actividad']
    if hasattr(actividad_id, 'id'): actividad = actividad_id
    else: actividad = get_object_or_404(Actividad, id=actividad_id)

    if request.method == 'POST':
        pago = Pago.objects.create(
            alumno=alumno,
            actividad=actividad,
            tipo=pago_data['tipo'],
            cantidad_clases=pago_data.get('cantidad_clases'),
            metodo=pago_data.get('metodo') or pago_data.get('método')
        )
        # Si el método es Mercado Pago, redirigimos al checkout automático
        if pago.metodo == Pago.MetodoPago.MERCADOPAGO:
            return redirect('pago_mercadopago_checkout', pago_id=pago.id)

        del request.session['pago_data']
        return redirect('gracias')
    
    return render(request, 'core/pago_confirmacion.html', {'pago_data': pago_data})


def gracias(request):
    """
    Pantalla de éxito.
    """
    return render(request, 'core/gracias.html')


@alumno_requerido
def pago_mercadopago_checkout(request, pago_id):
    """
    Genera la preferencia de pago en Mercado Pago y redirige al alumno.
    """
    pago = get_object_or_404(Pago, id=pago_id, alumno_id=request.session['alumno_id'])
    mp_service = MercadoPagoService()
    
    try:
        init_point = mp_service.crear_preferencia(pago)
        return redirect(init_point)
    except Exception as e:
        messages.error(request, f"Error al conectar con Mercado Pago: {str(e)}")
        return redirect('pago_metodo')


@csrf_exempt
def mercadopago_webhook(request):
    """
    Recibe notificaciones de pago desde la API de Mercado Pago.
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            # Mercado Pago envía notificaciones de tipo 'payment' e 'order'
            topic = request.GET.get("topic") or data.get("type")
            resource_id = request.GET.get("id") or (data.get("data", {}).get("id"))

            if topic == "payment" and resource_id:
                mp_service = MercadoPagoService()
                payment_info = mp_service.obtener_pago(resource_id)
                
                # Buscamos el pago en la base de datos usando external_reference
                pago_id = payment_info.get("external_reference")
                status = payment_info.get("status")
                
                if pago_id:
                    pago = Pago.objects.filter(id=pago_id).first()
                    if pago:
                        pago.mercado_pago_status = status
                        if status == "accredited":
                            pago.estado = Pago.EstadoPago.APROBADO
                        pago.save()
            
            return render(request, 'core/webhook_success.html', status=200) # O HttpResponse(status=200)
        except Exception as e:
            # En producción, loguear este error
            return render(request, 'core/webhook_error.html', status=500)

    return render(request, 'core/webhook_error.html', status=400)
