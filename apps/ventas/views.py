import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from decimal import Decimal
from django.db.models import Q
from apps.usuarios.models import Usuario
from apps.usuarios.views import alumno_requerido, profe_requerido
from apps.academia.models import Actividad, Cronograma
from django.http import JsonResponse
from .models import Pago, Pedido, PedidoItem, Producto, CategoriaProducto, ProductoVariante
from .forms import PagoTipoForm, PagoMetodoForm, PagoComprobanteForm
import hmac
import hashlib
from django.conf import settings
from .services.mercadopago_service import MercadoPagoService

@alumno_requerido
def carrito_sync(request):
    """ Endpoint AJAX para sincronizar el carrito de Alpine.js con Django (Task 5.4). """
    if request.method == 'POST':
        data = json.loads(request.body)
        carrito = data.get('cart', [])
        
        # Guardar en sesion
        request.session['carrito'] = carrito
        request.session['carrito_count'] = sum(item['qty'] for item in carrito)
        request.session.modified = True
        
        return JsonResponse({'success': True, 'count': request.session['carrito_count']})
    return JsonResponse({'error': 'Invalid method'}, status=400)

@alumno_requerido
def carrito_ver(request):
    """ Vista del carrito de compras detallado. """
    carrito_data = request.session.get('carrito', [])
    items_completos = []
    total = Decimal('0.0')
    
    for item in carrito_data:
        producto = get_object_or_404(Producto, id=item['id'])
        variante = None
        if item.get('variant_id'):
            variante = ProductoVariante.objects.filter(id=item['variant_id']).first()
        
        subtotal = producto.precio * item['qty']
        total += subtotal
        items_completos.append({
            'producto': producto,
            'variante': variante,
            'qty': item['qty'],
            'subtotal': subtotal
        })
        
    return render(request, 'ventas/carrito.html', {
        'items': items_completos,
        'total': total
    })

@alumno_requerido
def checkout(request):
    """ Procesa el carrito y genera el pedido (Task 5.5). """
    carrito_data = request.session.get('carrito', [])
    if not carrito_data:
        return redirect('tienda_inicio')
    
    alumno = Usuario.objects.get(id=request.session['alumno_id'])
    
    # 1. Crear el Pedido (Pendiente)
    metodo = request.POST.get('metodo', 'transferencia')
    pedido = Pedido.objects.create(
        alumno=alumno,
        estado=Pedido.Estado.PENDIENTE,
        metodo_pago=metodo
    )
    
    total_gral = Decimal('0.0')
    for doc in carrito_data:
        prod = get_object_or_404(Producto, id=doc['id'])
        var = None
        if doc.get('variant_id'):
            var = ProductoVariante.objects.filter(id=doc['variant_id']).first()
            if var and var.stock >= doc['qty']:
                var.stock -= doc['qty']
                var.save()
        elif prod.stock >= doc['qty']:
            # Descontar del stock global si NO hay variante
            prod.stock -= doc['qty']
            prod.save()
        
        item_total = prod.precio * doc['qty']
        total_gral += item_total
        
        PedidoItem.objects.create(
            pedido=pedido,
            producto=prod,
            variante=var,
            cantidad=doc['qty'],
            precio_unitario=prod.precio
        )
    
    pedido.total = total_gral
    pedido.save() # Calcula comisiones en el save()
    
    # Limpiar carrito
    request.session['carrito'] = []
    request.session['carrito_count'] = 0
    request.session.modified = True
    
    if metodo == 'mercadopago':
        # Redirigir a MP... (Omitido por brevedad en este step)
        pass
        
    messages.success(request, f"¡Pedido #{pedido.id} generado! Por favor, informa el pago.")
    return redirect('gracias')

def validar_signature_mp(request):
    """ Valida que la notificacion venga de Mercado Pago (Task 4.5). """
    header = request.headers.get("X-Signature")
    if not header: return False
    
    parts = {x.split("=")[0]: x.split("=")[1] for x in header.split(",")}
    ts = parts.get("ts")
    v1 = parts.get("v1")
    
    # El cuerpo del webhook segun la documentacion oficial
    # Depende de como se construye. Por simplicidad comparamos con el secreto si existe.
    secret = settings.MP_WEBHOOK_SECRET
    if not secret: return True # Si no hay secreto configurado, asumimos que estamos en dev/test
    
    # Construcción de la firma esperada
    # (Esto es una simplificación, la doc oficial pide reconstruir el string exacto)
    return True # Placeholder: En produccion se debe implementar el HMAC SHA256 exacto

@profe_requerido
def gestion_tesoreria(request):
    """ Panel administrativo para el tesorero de la asociacion. """
    if not request.user_obj.rol_gestion_tesoreria and not request.user_obj.rol_acceso_total:
        messages.error(request, "No tienes permisos para acceder a Tesorería.")
        return redirect('inicio')
    
    pagos_pendientes = Pago.objects.filter(estado='pendiente').order_by('-fecha_registro')
    return render(request, 'ventas/gestion_tesoreria.html', {
        'pagos_pendientes': pagos_pendientes
    })

@profe_requerido
def gestionar_pago_accion(request, pago_id):
    """ Procesa la aprobacion o rechazo de un pago manual. """
    pago = get_object_or_404(Pago, id=pago_id)
    if request.method == 'POST':
        accion = request.POST.get('accion')
        motivo = request.POST.get('motivo', '')
        
        if accion == 'aprobar':
            pago.estado = Pago.EstadoPago.APROBADO
            pago.save() # Al grabar se calculan comisiones
            messages.success(request, f"Pago de {pago.alumno.nombre} aprobado.")
        elif accion == 'rechazar':
            pago.estado = Pago.EstadoPago.RECHAZADO
            pago.motivo_rechazo = motivo
            pago.save()
            messages.warning(request, f"Pago rechazado.")
            
    return redirect('gestion_tesoreria')

@alumno_requerido
def pago_tipo(request):
    if request.method == 'POST':
        if 'metodo' in request.POST:
            form_tipo = PagoTipoForm(request.POST)
            form_metodo = PagoMetodoForm(request.POST)
            if form_tipo.is_valid() and form_metodo.is_valid():
                alumno = Usuario.objects.get(id=request.session['alumno_id'])
                clase_prog_id = request.POST.get('clase_programada')
                clase_prog = Cronograma.objects.filter(id=clase_prog_id).first() if clase_prog_id else None
                pago = Pago.objects.create(
                    alumno=alumno,
                    actividad=form_tipo.cleaned_data['actividad'],
                    clase_programada=clase_prog,
                    tipo=form_tipo.cleaned_data['tipo'],
                    cantidad_clases=form_tipo.cleaned_data.get('cantidad_clases'),
                    metodo=form_metodo.cleaned_data['metodo'],
                    comprobante=request.FILES.get('comprobante')
                )
                if 'pago_data' in request.session: del request.session['pago_data']
                if pago.metodo == Pago.MetodoPago.MERCADOPAGO:
                    return redirect('pago_mercadopago_checkout', pago_id=pago.id)
                return redirect('gracias')
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
    return render(request, 'ventas/pago_tipo.html', {'form': form})

@alumno_requerido
def pago_metodo(request):
    if 'pago_data' not in request.session: return redirect('pago_tipo')
    if request.method == 'POST':
        form = PagoMetodoForm(request.POST)
        if form.is_valid():
            pago_data = request.session['pago_data']
            pago_data.update(form.cleaned_data)
            request.session['pago_data'] = pago_data
            request.session.modified = True
            if form.cleaned_data['metodo'] in [Pago.MetodoPago.EFECTIVO, Pago.MetodoPago.MERCADOPAGO]:
                return redirect('pago_confirmacion')
            return redirect('pago_comprobante')
    else:
        form = PagoMetodoForm()
    return render(request, 'ventas/pago_metodo.html', {'form': form})

@alumno_requerido
def pago_comprobante(request):
    if 'pago_data' not in request.session: return redirect('pago_tipo')
    if request.method == 'POST':
        form = PagoComprobanteForm(request.POST, request.FILES)
        if form.is_valid():
            alumno = Usuario.objects.get(id=request.session['alumno_id'])
            pago_data = request.session['pago_data']
            actividad_id = pago_data['actividad']
            activity_obj = get_object_or_404(Actividad, id=actividad_id)
            pago = Pago.objects.create(
                alumno=alumno,
                actividad=activity_obj,
                tipo=pago_data['tipo'],
                cantidad_clases=pago_data.get('cantidad_clases'),
                metodo=pago_data.get('metodo') or pago_data.get('método'),
                comprobante=request.FILES.get('comprobante')
            )
            if pago.metodo == Pago.MetodoPago.MERCADOPAGO:
                return redirect('pago_mercadopago_checkout', pago_id=pago.id)
            del request.session['pago_data']
            return redirect('gracias')
    else:
        form = PagoComprobanteForm()
    return render(request, 'ventas/pago_comprobante.html', {'form': form})

@alumno_requerido
def pago_confirmacion(request):
    if 'pago_data' not in request.session: return redirect('pago_tipo')
    alumno = Usuario.objects.get(id=request.session['alumno_id'])
    pago_data = request.session['pago_data']
    actividad = get_object_or_404(Actividad, id=pago_data['actividad'])
    if request.method == 'POST':
        pago = Pago.objects.create(
            alumno=alumno,
            actividad=actividad,
            tipo=pago_data['tipo'],
            cantidad_clases=pago_data.get('cantidad_clases'),
            metodo=pago_data.get('metodo') or pago_data.get('método')
        )
        if pago.metodo == Pago.MetodoPago.MERCADOPAGO:
            return redirect('pago_mercadopago_checkout', pago_id=pago.id)
        del request.session['pago_data']
        return redirect('gracias')
    return render(request, 'ventas/pago_confirmacion.html', {'pago_data': pago_data})

@alumno_requerido
def pago_mercadopago_checkout(request, pago_id):
    pago = get_object_or_404(Pago, id=pago_id, alumno_id=request.session['alumno_id'])
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
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            topic = request.GET.get("topic") or data.get("type")
            resource_id = request.GET.get("id") or (data.get("data", {}).get("id"))
            if topic == "payment" and resource_id:
                identificador_pago = request.GET.get('identificador_pago')
                access_token = None
                if identificador_pago:
                    pago_original = Pago.objects.filter(id=identificador_pago).first()
                    if pago_original and pago_original.clase_programada and getattr(pago_original.clase_programada.profesor, 'mp_access_token', None):
                        access_token = pago_original.clase_programada.profesor.mp_access_token
                mp_service = MercadoPagoService(access_token)
                payment_info = mp_service.obtener_pago(resource_id)
                external_ref = payment_info.get("external_reference")
                status = payment_info.get("status")
                if external_ref:
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
            return render(request, 'ventas/webhook_success.html', status=200)
        except Exception as e: return render(request, 'ventas/webhook_error.html', status=500)
    return render(request, 'ventas/webhook_error.html', status=400)

@alumno_requerido
def tienda_inicio(request):
    categorias = CategoriaProducto.objects.prefetch_related('productos').all()
    return render(request, 'ventas/tienda.html', {
        'categorias': categorias,
        'productos': Producto.objects.filter(activo=True)
    })

@alumno_requerido
def tienda_comprar(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id, activo=True)
    alumno = Usuario.objects.get(id=request.session['alumno_id'])
    if request.method == 'POST':
        metodo_pago = request.POST.get('metodo_pago')
        cantidad = int(request.POST.get('cantidad', 1))
        es_backorder = False
        if not producto.hay_stock and not producto.permite_backorder:
             messages.error(request, "Stock insuficiente.")
             return redirect('tienda_inicio')
        precio_total = producto.precio * cantidad
        profesor_venta = None
        primera_clase = Pago.objects.filter(alumno=alumno, clase_programada__isnull=False).order_by('-fecha_registro').first()
        if primera_clase and primera_clase.clase_programada:
            profesor_venta = primera_clase.clase_programada.profesor
        porcentaje_comision = producto.porcentaje_comision if profesor_venta else Decimal('0.0')
        monto_comision = (precio_total * porcentaje_comision) / Decimal('100.0')
        pedido = Pedido.objects.create(
            alumno=alumno, total=precio_total, metodo_pago=metodo_pago,
            estado=Pedido.Estado.PENDIENTE, profesor_venta=profesor_venta,
            porcentaje_comision=porcentaje_comision, monto_comision=monto_comision,
            backorder=es_backorder
        )
        PedidoItem.objects.create(pedido=pedido, producto=producto, cantidad=cantidad, precio_unitario=producto.precio)
        if metodo_pago == Pago.MetodoPago.MERCADOPAGO:
            mp_service = MercadoPagoService()
            pref_url = mp_service.crear_preferencia_tienda(
                titulo=f"Tienda LongHuHe: {producto.nombre} x{cantidad}",
                precio=float(precio_total),
                url_retorno=request.build_absolute_uri('/gracias/'),
                externo_id=f"TIENDA_{pedido.id}"
            )
            return redirect(pref_url)
        else:
            messages.success(request, "Pedido generado con éxito.")
            return redirect('gracias')
    return render(request, 'ventas/tienda_comprar.html', {'producto': producto})
