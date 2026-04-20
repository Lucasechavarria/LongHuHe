import json
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from decimal import Decimal
from apps.usuarios.models import Usuario
from apps.usuarios.views import alumno_requerido, profe_requerido
from apps.academia.models import Actividad
from django.http import JsonResponse
from .models import Pago, Pedido, PedidoItem, Producto, CategoriaProducto, ProductoVariante
from .forms import PagoTipoForm, PagoMetodoForm, PagoComprobanteForm
from django.conf import settings
from django.db import transaction
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from .services.mercadopago_service import MercadoPagoService
import csv
from django.http import HttpResponse

@alumno_requerido
def gracias(request):
    """ Vista de éxito genérica para pagos y pedidos con feedback. """
    pedido_id = request.GET.get('pedido_id')
    pago_id = request.GET.get('pago_id')
    
    pedido = None
    if pedido_id:
        pedido = Pedido.objects.filter(pk=pedido_id, alumno=request.user_obj).first()
    
    return render(request, 'ventas/gracias.html', {
        'alumno': request.user_obj,
        'pedido': pedido
    })

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
@transaction.atomic
def checkout(request):
    """ Procesa el carrito y genera el pedido (Task 5.5). """
    carrito_data = request.session.get('carrito', [])
    if not carrito_data:
        return redirect('tienda_inicio')
    
    alumno = request.user_obj
    metodo = request.POST.get('metodo', 'transferencia')
    
    # 1. Crear el Pedido (Pendiente)
    pedido = Pedido.objects.create(
        alumno=alumno,
        estado=Pedido.Estado.PENDIENTE,
        metodo_pago=metodo
    )
    
    total_gral = Decimal('0.0')
    tiene_backorder = False

    for doc in carrito_data:
        # Bloqueamos el producto y la variante para que nadie más los mueva durante la transacción
        prod = get_object_or_404(Producto.objects.select_for_update(), id=doc['id'])
        var = None
        qty = int(doc['qty'])
        
        if doc.get('variant_id'):
            var = get_object_or_404(ProductoVariante.objects.select_for_update(), id=doc['variant_id'])
            if var.stock < qty:
                if not prod.permite_backorder:
                    transaction.set_rollback(True)
                    messages.warning(request, f"¡Error! Por milisegundos alguien más se llevó lo último de {prod.nombre} ({var.talle}).")
                    return redirect('carrito_ver')
                else:
                    tiene_backorder = True
        elif prod.stock < qty:
            if not prod.permite_backorder:
                transaction.set_rollback(True)
                messages.warning(request, f"¡Error! Por milisegundos alguien más se llevó lo último de {prod.nombre}.")
                return redirect('carrito_ver')
            else:
                tiene_backorder = True
        
        item_total = prod.precio * qty
        total_gral += item_total
        
        PedidoItem.objects.create(
            pedido=pedido,
            producto=prod,
            variante=var,
            cantidad=qty,
            precio_unitario=prod.precio
        )
    
    pedido.total = total_gral
    pedido.backorder = tiene_backorder
    pedido.save() # Calcula comisiones (ahora sin recursión)
    
    # Limpiar carrito de la sesión (el localStorage se limpia en la vista 'gracias')
    request.session['carrito'] = []
    request.session['carrito_count'] = 0
    request.session.modified = True
    
    if metodo == 'mercadopago':
        try:
            mp = MercadoPagoService()
            init_point = mp.crear_preferencia_tienda(
                titulo=f"Pedido #{pedido.id} - Academia LHH",
                precio=float(pedido.total),
                url_retorno=request.build_absolute_uri(reverse('gracias') + f"?pedido_id={pedido.id}"),
                externo_id=pedido.id
            )
            return redirect(init_point)
        except Exception as e:
            print(f"Error MP Tienda: {e}")
            messages.warning(request, "Error al conectar con Mercado Pago. Tu pedido quedó registrado, coordina el pago con tu profesor.")
    
    return redirect(reverse('gracias') + f"?pedido_id={pedido.id}")

def validar_signature_mp(request):
    """
    Valida que la notificación del webhook sea genuina de Mercado Pago.
    Implementación oficial HMAC-SHA256:
    https://www.mercadopago.com.ar/developers/es/docs/your-integrations/notifications/webhooks
    """
    import hmac
    import hashlib

    secret = settings.MP_WEBHOOK_SECRET
    if not secret:
        # Sin secreto configurado: aceptar en desarrollo, rechazar en producción
        if settings.DEBUG:
            return True
        return False

    header = request.headers.get("x-signature", "")
    request_id = request.headers.get("x-request-id", "")

    if not header:
        return False

    # Parsear el header: "ts=<timestamp>,v1=<hash>"
    parts = {}
    for part in header.split(","):
        if "=" in part:
            k, v = part.split("=", 1)
            parts[k.strip()] = v.strip()

    ts = parts.get("ts", "")
    v1 = parts.get("v1", "")

    if not ts or not v1:
        return False

    # Extraer el resource_id del body o la querystring
    data_id = request.GET.get("data.id") or request.GET.get("id", "")

    # Construir el string a firmar según la spec oficial de MP
    # Formato: "id:[data.id];request-id:[x-request-id];ts:[ts];"
    manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"

    expected = hmac.new(
        secret.encode("utf-8"),
        msg=manifest.encode("utf-8"),
        digestmod=hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected, v1)

@profe_requerido
def gestion_tesoreria(request):
    """ Panel administrativo para el tesorero de la asociacion con Dashboard de Métricas. """
    if not request.user_obj.rol_gestion_tesoreria and not request.user_obj.rol_acceso_total:
        messages.error(request, "No tienes permisos para acceder a Tesorería.")
        return redirect('inicio')
    
    from datetime import timedelta
    
    hoy = timezone.now().date()
    hace_30_dias = hoy - timedelta(days=30)
    
    # 1. KPIs Principales
    pagos_aprobados_mes = Pago.objects.filter(
        estado=Pago.EstadoPago.APROBADO, 
        fecha_registro__date__month=hoy.month,
        fecha_registro__date__year=hoy.year
    )
    pedidos_pagados_mes = Pedido.objects.filter(
        estado__in=[Pedido.Estado.PAGADO, Pedido.Estado.ENTREGADO],
        fecha_registro__date__month=hoy.month,
        fecha_registro__date__year=hoy.year
    )
    
    ingresos_pagos = pagos_aprobados_mes.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
    ingresos_pedidos = pedidos_pagados_mes.aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    ingresos_totales_mes = ingresos_pagos + ingresos_pedidos
    
    pendientes_count = Pago.objects.filter(estado=Pago.EstadoPago.PENDIENTE).count()
    pendientes_monto = Pago.objects.filter(estado=Pago.EstadoPago.PENDIENTE).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
    
    # 2. Tendencia Diaria (Últimos 30 días)
    tendencia_data = Pago.objects.filter(
        estado=Pago.EstadoPago.APROBADO,
        fecha_registro__date__gte=hace_30_dias
    ).annotate(date=TruncDate('fecha_registro')).values('date').annotate(
        total=Sum('monto')
    ).order_by('date')
    
    chart_labels = [d['date'].strftime("%d/%m") for d in tendencia_data]
    chart_values = [float(d['total']) for d in tendencia_data]
    
    # 3. Métodos de Pago
    metodos_data = Pago.objects.filter(estado=Pago.EstadoPago.APROBADO).values('metodo').annotate(count=Count('id'))
    metodos_labels = [dict(Pago.MetodoPago.choices).get(d['metodo'], d['metodo']) for d in metodos_data]
    metodos_values = [d['count'] for d in metodos_data]
    
    pagos_pendientes = Pago.objects.filter(estado=Pago.EstadoPago.PENDIENTE).order_by('-fecha_registro')
    
    return render(request, 'ventas/gestion_tesoreria.html', {
        'pagos_pendientes': pagos_pendientes,
        'kpis': {
            'ingresos_mes': ingresos_totales_mes,
            'pendientes_count': pendientes_count,
            'pendientes_monto': pendientes_monto,
        },
        'chart_data': {
            'labels': chart_labels,
            'values': chart_values,
            'metodos_labels': metodos_labels,
            'metodos_values': metodos_values,
        }
    })

@profe_requerido
def exportar_tesoreria_csv(request):
    """ Genera un reporte CSV de los pagos aprobados del mes actual (Sprint 12). """
    if not request.user_obj.rol_gestion_tesoreria and not request.user_obj.rol_acceso_total:
        return HttpResponse("No autorizado", status=403)

    hoy = timezone.now().date()
    pagos = Pago.objects.filter(
        estado=Pago.EstadoPago.APROBADO,
        fecha_registro__date__month=hoy.month,
        fecha_registro__date__year=hoy.year
    ).select_related('alumno', 'actividad')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="tesoreria_{hoy.strftime("%Y_%m")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Fecha', 'Alumno', 'Tipo', 'Monto', 'Método', 'Actividad'])

    for p in pagos:
        writer.writerow([
            p.fecha_registro.strftime("%Y-%m-%d %H:%M"),
            p.alumno.nombre_completo,
            p.get_tipo_display(),
            p.monto,
            p.get_metodo_display(),
            p.actividad.nombre if p.actividad else "Tienda/Otro"
        ])

    return response

@profe_requerido
@transaction.atomic
def gestionar_pago_accion(request, pago_id):
    """ Procesa la aprobacion o rechazo de un pago manual. """
    pago = get_object_or_404(Pago.objects.select_for_update(), id=pago_id)
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
            messages.warning(request, "Pago rechazado.")
            
    return redirect('gestion_tesoreria')

@alumno_requerido
def pago_tipo(request):
    """ Task 2.1: Selección de Actividad y Tipo de Pago (Flujo Limpio) """
    alumno = request.user_obj
    
    if request.method == 'POST':
        form = PagoTipoForm(request.POST, alumno=alumno)
        if form.is_valid():
            pago_data = form.cleaned_data
            # Convertir objetos a IDs para serialización en sesión
            if 'actividad' in pago_data and hasattr(pago_data['actividad'], 'id'):
                pago_data['actividad'] = pago_data['actividad'].id
            
            # Guardamos en sesión y avanzamos al siguiente paso
            request.session['pago_data'] = pago_data
            request.session.modified = True
            return redirect('pago_metodo')
    else:
        # Pre-seleccionar si el alumno solo tiene una actividad autorizada
        actividades_alumno = alumno.actividades.all()
        initial = {}
        if actividades_alumno.count() == 1:
            initial['actividad'] = actividades_alumno.first()
        
        form = PagoTipoForm(alumno=alumno, initial=initial)
        
    return render(request, 'ventas/pago_tipo.html', {'form': form, 'alumno': alumno})

@alumno_requerido
def pago_metodo(request):
    if 'pago_data' not in request.session:
        return redirect('pago_tipo')
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
    alumno = Usuario.objects.get(id=request.session['alumno_id'])
    return render(request, 'ventas/pago_metodo.html', {'form': form, 'alumno': alumno})

@alumno_requerido
def pago_comprobante(request):
    if 'pago_data' not in request.session:
        return redirect('pago_tipo')
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
    alumno = Usuario.objects.get(id=request.session['alumno_id'])
    return render(request, 'ventas/pago_comprobante.html', {'form': form, 'alumno': alumno})

@alumno_requerido
def pago_confirmacion(request):
    if 'pago_data' not in request.session:
        return redirect('pago_tipo')
    
    alumno = request.user_obj
    pago_data = request.session['pago_data']
    actividad = get_object_or_404(Actividad, id=pago_data['actividad'])
    
    # Calcular monto base
    monto_base = Decimal('0.00')
    if pago_data['tipo'] == Pago.TipoPago.MES:
        monto_base = actividad.precio_mes
    elif pago_data['tipo'] == Pago.TipoPago.CLASE_SUELTA:
        monto_base = actividad.precio_clase
    elif pago_data['tipo'] == Pago.TipoPago.PAQUETE:
        monto_base = actividad.precio_clase * (pago_data.get('cantidad_clases') or 1)
    
    # 2. Gestionar cupón existente en sesión o nuevo
    descuento_id = pago_data.get('descuento_id')
    monto_desc = Decimal('0.00')
    
    if descuento_id:
        from .models import Descuento
        desc_obj = Descuento.objects.filter(id=descuento_id, activo=True).first()
        if desc_obj and desc_obj.esta_vigente and desc_obj.monto_minimo_pago <= monto_base:
            # Validar que siga siendo aplicable al nuevo tipo (por si cambió en el medio)
            if desc_obj.aplicable_a == 'todos' or desc_obj.aplicable_a == pago_data['tipo']:
                monto_desc = desc_obj.calcular_descuento(monto_base)
                pago_data['monto_descontado'] = float(monto_desc)
            else:
                # Ya no es aplicable, limpiar
                del pago_data['descuento_id']
                if 'monto_descontado' in pago_data:
                    del pago_data['monto_descontado']
                messages.warning(request, "El cupón previo no aplica a este nuevo tipo de pago.")
        else:
            # Ya no es válido, limpiar
            del pago_data['descuento_id']
            if 'monto_descontado' in pago_data:
                del pago_data['monto_descontado']

    if request.method == 'POST':
        accion = request.POST.get('accion')
        
        # A. VALIDAR CUPÓN (Nuevo o reemplazo)
        if accion == 'validar_cupon':
            codigo = request.POST.get('codigo_descuento', '').strip().upper()
            from .models import Descuento
            descuento_obj = Descuento.objects.filter(codigo=codigo, activo=True).first()
            
            if not descuento_obj:
                messages.error(request, "El código de cupón no es válido o ya no está activo.")
            elif not descuento_obj.esta_vigente:
                messages.error(request, "Este cupón ha expirado o ya no tiene usos disponibles.")
            elif descuento_obj.monto_minimo_pago > monto_base:
                messages.error(request, f"Este cupón requiere una compra mínima de ${descuento_obj.monto_minimo_pago}.")
            elif descuento_obj.aplicable_a != 'todos' and descuento_obj.aplicable_a != pago_data['tipo']:
                messages.error(request, f"Este cupón solo es válido para: {descuento_obj.get_aplicable_a_display()}.")
            else:
                pago_data['descuento_id'] = descuento_obj.id
                monto_desc = descuento_obj.calcular_descuento(monto_base)
                pago_data['monto_descontado'] = float(monto_desc)
                request.session.modified = True
                messages.success(request, f"Cupón '{descuento_obj.nombre}' aplicado correctamente.")
            
            monto_total = (monto_base - monto_desc).quantize(Decimal('0.01'))
            return render(request, 'ventas/pago_confirmacion.html', {
                'pago_data': pago_data, 
                'actividad': actividad, 
                'monto_base': monto_base,
                'monto_total': monto_total
            })

        # B. CONFIRMAR PAGO
        elif accion == 'confirmar':
            pago = Pago.objects.create(
                alumno=alumno,
                actividad=actividad,
                tipo=pago_data['tipo'],
                cantidad_clases=pago_data.get('cantidad_clases'),
                metodo=pago_data.get('metodo') or pago_data.get('método'),
                descuento_id=pago_data.get('descuento_id')
            )
            
            if pago.metodo == Pago.MetodoPago.MERCADOPAGO:
                return redirect('pago_mercadopago_checkout', pago_id=pago.id)
            
            del request.session['pago_data']
            messages.success(request, "Pago registrado. Por favor informa el comprobante si fue transferencia.")
            return redirect('gracias')

    monto_total = (monto_base - monto_desc).quantize(Decimal('0.01'))
    return render(request, 'ventas/pago_confirmacion.html', {
        'pago_data': pago_data, 
        'actividad': actividad, 
        'monto_base': monto_base,
        'monto_total': monto_total
    })

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
    except Exception:
        messages.error(request, "Error al conectar con Mercado Pago.")
        return redirect('pago_metodo')

@csrf_exempt
def mercadopago_webhook(request):
    if request.method != "POST":
        return JsonResponse({'status': 'bad_request'}, status=400)

    # ✅ Validación de firma HMAC-SHA256 oficial de Mercado Pago
    if not validar_signature_mp(request):
        return JsonResponse({'status': 'forbidden', 'detail': 'Firma inválida'}, status=400)

    try:
        data = json.loads(request.body)
        topic = request.GET.get("topic") or data.get("type")
        resource_id = request.GET.get("id") or (data.get("data", {}).get("id"))

        if topic == "payment" and resource_id:
            with transaction.atomic():
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
                        # LOCK del Pedido para procesar secuencialmente
                        pedido = Pedido.objects.select_for_update().filter(id=pedido_id).first()
                        if pedido and pedido.estado != Pedido.Estado.PAGADO:
                            pedido.mercado_pago_status = status
                            pedido.mercado_pago_id = resource_id
                            if status in ("accredited", "approved"):
                                pedido.estado = Pedido.Estado.PAGADO
                            pedido.save()
                    else:
                        # LOCK del Pago para procesar secuencialmente
                        pago = Pago.objects.select_for_update().filter(id=external_ref).first()
                        if pago and pago.estado != Pago.EstadoPago.APROBADO:
                            pago.mercado_pago_status = status
                            pago.mercado_pago_id = resource_id
                            if status in ("accredited", "approved"):
                                pago.estado = Pago.EstadoPago.APROBADO
                            pago.save()
        return JsonResponse({'status': 'ok'}, status=200)
    except Exception as e:
        return JsonResponse({'status': 'error', 'detail': str(e)}, status=500)

@alumno_requerido
def tienda_inicio(request):
    # Consulta simplificada para evitar errores de prefetch complejo en producción
    categorias = CategoriaProducto.objects.all().prefetch_related('productos')
    
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
                url_retorno=request.build_absolute_uri(reverse('gracias')),
                externo_id=f"TIENDA_{pedido.id}"
            )
            return redirect(pref_url)
        else:
            messages.success(request, "Pedido generado con éxito.")
            return redirect('gracias')
    return render(request, 'ventas/tienda_comprar.html', {'producto': producto})

@alumno_requerido
def pago_historial(request):
    """
    Lista todos los pagos y pedidos realizados por el alumno.
    """
    from .models import Pago, Pedido
    alumno = request.user_obj
    
    pagos = Pago.objects.filter(alumno=alumno).order_by('-fecha_registro')
    pedidos = Pedido.objects.filter(alumno=alumno).order_by('-fecha_registro')
    
    return render(request, 'ventas/historial.html', {
        'pagos': pagos,
        'pedidos': pedidos,
        'alumno': alumno,
        'hoy': timezone.now().date()
    })
