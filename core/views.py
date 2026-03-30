from django.db import models
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Usuario, Asistencia, Pago, Locacion, Actividad, ClaseProgramada, Producto, CategoriaProducto, Pedido, PedidoItem
from .forms import AlumnoOnboardingForm, PagoTipoForm, PagoMetodoForm, PagoComprobanteForm
from .services.mercadopago_service import MercadoPagoService # Importar el servicio
from functools import wraps
from django.views.decorators.csrf import csrf_exempt # Para el webhook
import json

def profe_requerido(view_func):
    """
    Decorador para asegurar que el usuario es profesor.
    Requiere que esté logueado (sesión o Django Auth).
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Primero revisamos si hay alumno_id en sesión y si es profe
        if 'alumno_id' in request.session:
            usuario = Usuario.objects.filter(id=request.session['alumno_id']).first()
            if usuario and usuario.es_profe:
                request.user_obj = usuario # Guardamos el objeto para la vista
                return view_func(request, *args, **kwargs)
        
        # Si no, probamos con el request.user estándar (admin/staff que también es profe)
        if request.user.is_authenticated and getattr(request.user, 'es_profe', False):
            request.user_obj = request.user
            return view_func(request, *args, **kwargs)
            
        messages.error(request, "Acceso restringido solo para profesores.")
        return redirect('inicio')
    return _wrapped_view

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
    
    clases_programadas = ClaseProgramada.objects.filter(
        locacion=alumno.locacion,
        actividad__in=alumno.actividades.all()
    ).select_related('profesor', 'actividad').prefetch_related('horarios').order_by('actividad__nombre', 'profesor__nombre')

    return render(request, 'core/inicio.html', {
        'alumno': alumno,
        'locaciones': locaciones,
        'clases_programadas': clases_programadas
    })


@alumno_requerido
def registrar_asistencia(request):
    """
    Registra la asistencia y redirige a gracias. (Hecho por el alumno).
    """
    if request.method == 'POST':
        alumno = Usuario.objects.get(id=request.session['alumno_id'])
        actividad_id = request.POST.get('actividad_id')
        actividad = get_object_or_404(Actividad, id=actividad_id)
        Asistencia.objects.create(alumno=alumno, actividad=actividad)
        messages.success(request, f"¡Asistencia a {actividad.nombre} registrada!")
        return redirect('gracias')
    return redirect('inicio')


@profe_requerido
def escanear_qr_alumno(request, alumno_id):
    """
    Vista a la que llega el profesor al escanear el QR del alumno.
    Muestra el estado de deuda ("Cartel Emergente") y permite registrar la asistencia.
    """
    alumno = get_object_or_404(Usuario, id=alumno_id)
    
    # Obtenemos el profesor actual (del decorador)
    profesor = request.user_obj
    
    # Obtenemos las clases que este profesor dicta y donde el alumno podría asistir
    # Para el MVP, mostramos todas las actividades que coinciden entre alumno y profesor
    actividades_profesor = Actividad.objects.filter(clases_asignadas__profesor=profesor).distinct()
    actividades_comunes = alumno.actividades.filter(id__in=actividades_profesor)

    if request.method == 'POST':
        # El profesor confirma la asistencia
        actividad_id = request.POST.get('actividad_id')
        actividad = get_object_or_404(Actividad, id=actividad_id)
        
        # NO registramos si está vencido y el sistema es estricto
        if alumno.estado_morosidad == 'vencido':
            messages.error(request, "Alumno VENCIDO. No puede registrar asistencia hasta regularizar el pago.")
        else:
            Asistencia.objects.create(alumno=alumno, actividad=actividad)
            messages.success(request, f"Asistencia de {alumno.nombre_completo} registrada correctamente.")
        
        return redirect('escanear_qr_alumno', alumno_id=alumno.id)

    return render(request, 'core/escanear_qr.html', {
        'alumno_qr': alumno,
        'actividades_comunes': actividades_comunes
    })


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
                
                # Triangulación Perfecta: Ligar con la clase específica
                clase_prog_id = request.POST.get('clase_programada')
                clase_prog = ClaseProgramada.objects.filter(id=clase_prog_id).first() if clase_prog_id else None
                
                pago = Pago.objects.create(
                    alumno=alumno,
                    actividad=form_tipo.cleaned_data['actividad'],
                    clase_programada=clase_prog,
                    tipo=form_tipo.cleaned_data['tipo'],
                    cantidad_clases=form_tipo.cleaned_data.get('cantidad_clases'),
                    metodo=form_metodo.cleaned_data['metodo'],
                    comprobante=request.FILES.get('comprobante')
                )
                
                if 'pago_data' in request.session:
                    del request.session['pago_data']
                    
                # Si el método es Mercado Pago, redirigimos al checkout Automático
                if pago.metodo == Pago.MetodoPago.MERCADOPAGO:
                    return redirect('pago_mercadopago_checkout', pago_id=pago.id)
                    
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
    
    # Triangulación Perfecta: Buscar token del profesor si exite clase programada
    access_token = None
    if pago.clase_programada and getattr(pago.clase_programada.profesor, 'mp_access_token', None):
        access_token = pago.clase_programada.profesor.mp_access_token
        
    mp_service = MercadoPagoService(access_token)
    
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
                # Recibimos el parámetro para saber si es de clase o de tienda
                identificador_pago = request.GET.get('identificador_pago')
                identificador_tienda = request.GET.get('identificador_tienda')
                
                access_token = None
                
                # 1. Pago de Clase (Usa token del profesor si existe)
                if identificador_pago:
                    pago_original = Pago.objects.filter(id=identificador_pago).first()
                    if pago_original and pago_original.clase_programada and getattr(pago_original.clase_programada.profesor, 'mp_access_token', None):
                        access_token = pago_original.clase_programada.profesor.mp_access_token
                        
                # 2. Pago de Tienda (Usa token central, no sobreescribimos access_token)
                # (Si tuviéramos franquicias, aquí se buscaría el token de la franquicia)
                
                mp_service = MercadoPagoService(access_token)
                payment_info = mp_service.obtener_pago(resource_id)
                
                # Buscamos el pago en la base de datos usando external_reference
                external_ref = payment_info.get("external_reference")
                status = payment_info.get("status")
                
                if external_ref:
                    # Discriminamos si es Tienda o Pago Normal
                    if external_ref.startswith('TIENDA_'):
                        pedido_id = external_ref.replace('TIENDA_', '')
                        pedido = Pedido.objects.filter(id=pedido_id).first()
                        if pedido:
                            pedido.mercado_pago_status = status
                            pedido.mercado_pago_id = resource_id
                            if status == "accredited" or status == "approved":
                                pedido.estado = Pedido.Estado.PAGADO
                            pedido.save()
                    else:
                        pago = Pago.objects.filter(id=external_ref).first()
                        if pago:
                            pago.mercado_pago_status = status
                            pago.mercado_pago_id = resource_id
                            if status == "accredited" or status == "approved":
                                pago.estado = Pago.EstadoPago.APROBADO
                            pago.save()
            
            return render(request, 'core/webhook_success.html', status=200) # O HttpResponse(status=200)
        except Exception as e:
            # En producción, loguear este error
            return render(request, 'core/webhook_error.html', status=500)

    return render(request, 'core/webhook_error.html', status=400)


# =========================================================
# FASE 3: Vistas de Tienda E-Commerce
# =========================================================

@alumno_requerido
def tienda_inicio(request):
    """
    Muestra los productos disponibles en la tienda.
    Oculta los que tienen activo=False.
    """
    categorias = CategoriaProducto.objects.prefetch_related('productos').all()
    # Filtramos productos activos para la vista
    # Pasamos las categorías y los productos
    return render(request, 'core/tienda.html', {
        'categorias': categorias,
        'productos': Producto.objects.filter(activo=True)
    })

@alumno_requerido
def tienda_comprar(request, producto_id):
    """
    Flujo rápido de compra de 1 producto.
    Si el método es Mercado Pago, delega al servicio central (sin token de profe).
    """
    from decimal import Decimal
    producto = get_object_or_404(Producto, id=producto_id, activo=True)
    alumno = Usuario.objects.get(id=request.session['alumno_id'])
    
    if request.method == 'POST':
        metodo_pago = request.POST.get('metodo_pago')
        cantidad = int(request.POST.get('cantidad', 1))
        
        # Validación de Backorder
        es_backorder = False
        if producto.stock < cantidad:
            if not producto.permite_backorder:
                messages.error(request, "Stock insuficiente y el artículo no permite reservas.")
                return redirect('tienda_inicio')
            es_backorder = True
            
        precio_total = producto.precio * cantidad
        
        # Calculamos la comisión para el profesor actual del alumno.
        profesor_venta = None
        primera_clase = Pago.objects.filter(
            alumno=alumno, 
            clase_programada__isnull=False
        ).order_by('-fecha_registro').first()
        
        if primera_clase and primera_clase.clase_programada:
            profesor_venta = primera_clase.clase_programada.profesor
            
        # Comision default 10% para el profesor
        porcentaje_comision = Decimal('10.0') if profesor_venta else Decimal('0.0')
        monto_comision = (precio_total * porcentaje_comision) / Decimal('100.0')

        pedido = Pedido.objects.create(
            alumno=alumno,
            total=precio_total,
            metodo_pago=metodo_pago,
            estado=Pedido.Estado.PENDIENTE,
            profesor_venta=profesor_venta,
            porcentaje_comision=porcentaje_comision,
            monto_comision=monto_comision,
            backorder=es_backorder
        )
        
        PedidoItem.objects.create(
            pedido=pedido,
            producto=producto,
            cantidad=cantidad,
            precio_unitario=producto.precio
        )
        
        # Descontamos stock (puede quedar negativo si hay backorder)
        producto.stock -= cantidad
        producto.save()
        
        # Si es MP, redirigimos a gateway. Si no, a confirmación manual (gracias).
        if metodo_pago == Pago.MetodoPago.MERCADOPAGO:
            # MVP: Creamos una preferencia MP central
            from .services.mercadopago_service import MercadoPagoService
            # Para la tienda, la cuenta es la de la asociación (sin access_token sobreescrito)
            mp_service = MercadoPagoService()
            pref_url = mp_service.crear_preferencia_tienda(
                titulo=f"Tienda LongHuHe: {producto.nombre} x{cantidad}",
                precio=float(precio_total),
                url_retorno=request.build_absolute_uri('/gracias/'),
                externo_id=f"TIENDA_{pedido.id}"
            )
            return redirect(pref_url)
            
        else:
            messages.success(request, f"Pedido generado con éxito. Entrégaselo a tu profesor o al encargado.")
            return redirect('gracias')

    return render(request, 'core/tienda_comprar.html', {
        'producto': producto
    })
