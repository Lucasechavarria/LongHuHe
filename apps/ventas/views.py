import json
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import timedelta
from django.core.files.base import ContentFile
from decimal import Decimal
from apps.usuarios.models import Usuario
from apps.usuarios.views import alumno_requerido, profe_requerido, requiere_rol
from apps.academia.models import Actividad
from django.http import JsonResponse
from .models import Pago, Pedido, Producto, CategoriaProducto, ProductoVariante, CierreCaja
from .forms import PagoTipoForm, PagoMetodoForm, PagoComprobanteForm
from django.conf import settings
from django.db import transaction
from django.db.models import Sum
from .services.payments.factory import PaymentGatewayFactory
import csv
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from django.http import HttpResponse

@alumno_requerido
def gracias(request):
    """ Vista de éxito genérica para pagos y pedidos con feedback. """
    pedido_id = request.GET.get('pedido_id')
    
    pedido = None
    if pedido_id and pedido_id.isdigit():
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
    
    # 1. Crear el Pedido (Pendiente) y Procesar Carrito vía Service Layer
    from .services.tienda_service import TiendaService
    try:
        pedido = TiendaService.crear_pedido_desde_carrito(alumno, carrito_data, metodo)
    except ValueError as e:
        messages.warning(request, str(e))
        return redirect('carrito_ver')
    
    # Limpiar carrito de la sesión (el localStorage se limpia en la vista 'gracias')
    request.session['carrito'] = []
    request.session['carrito_count'] = 0
    request.session.modified = True
    
    if metodo == 'mercadopago':
        try:
            gateway = PaymentGatewayFactory.get_gateway()
            init_point = gateway.crear_preferencia_tienda(
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
@requiere_rol('rol_gestion_tesoreria')
def gestion_tesoreria(request):
    """ Panel administrativo para el tesorero de la asociacion con Dashboard de Métricas. """
    
    hoy = timezone.now().date()
    
    # --- AUTO-CIERRE PEREZOSO (Task 12.2 / Sprint Automático) ---
    # Verificamos si el mes anterior está cerrado. Si no, lo cerramos automáticamente.
    primer_dia_este_mes = hoy.replace(day=1)
    ultimo_dia_mes_pasado = primer_dia_este_mes - timedelta(days=1)
    
    mes_pasado = ultimo_dia_mes_pasado.month
    anio_pasado = ultimo_dia_mes_pasado.year
    
    if not CierreCaja.objects.filter(mes=mes_pasado, anio=anio_pasado).exists():
        try:
            with transaction.atomic():
                # Ejecutar cierre automático
                pagos_pasado = Pago.objects.filter(
                    estado=Pago.EstadoPago.APROBADO,
                    fecha_registro__month=mes_pasado,
                    fecha_registro__year=anio_pasado
                )
                total_pasado = pagos_pasado.aggregate(Sum('monto'))['monto__sum'] or Decimal('0.00')
                
                # Generamos el buffer PDF del mes pasado
                buffer = generar_pdf_tesoreria(mes_pasado, anio_pasado)
                
                cierre = CierreCaja(
                    mes=mes_pasado,
                    anio=anio_pasado,
                    total_recaudado=total_pasado,
                    usuario_genero=request.user_obj
                )
                filename = f"cierre_auto_{anio_pasado}_{mes_pasado}.pdf"
                cierre.archivo_pdf.save(filename, ContentFile(buffer.getvalue()), save=True)
                # Al usar save=True en .save(), ya se persiste el objeto completo.
        except Exception as e:
            # Si falla el auto-cierre, logueamos pero no mostramos error 500
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error en auto-cierre de tesorería: {e}", exc_info=True)
    
    # 1. KPIs Principales (Métricas Globales del Mes)
    from .selectors import TesoreriaSelector
    kpis_mes = TesoreriaSelector.obtener_kpis_mes(hoy.month, hoy.year)
    ingresos_totales_mes = kpis_mes['ingresos_totales']
    ingresos_pagos = kpis_mes['ingresos_pagos']
    ingresos_pedidos = kpis_mes['ingresos_pedidos']
    
    pendientes_count = Pago.objects.filter(estado=Pago.EstadoPago.PENDIENTE).count()
    pendientes_monto = Pago.objects.filter(estado=Pago.EstadoPago.PENDIENTE).aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
    
    # 2. Tendencia Diaria (Últimos 30 días)
    tendencia = TesoreriaSelector.obtener_tendencia_diaria()
    chart_labels = tendencia['labels']
    chart_values = tendencia['values']
    
    # 3. Métodos de Pago
    dist_metodos = TesoreriaSelector.obtener_distribucion_metodos()
    metodos_labels = dist_metodos['labels']
    metodos_values = dist_metodos['values']
    
    # 4. Desglose por Actividad (KPIs Solicitados)
    ingresos_por_actividad = TesoreriaSelector.obtener_ingresos_por_actividad(hoy.month, hoy.year)
    stats_tipos = TesoreriaSelector.obtener_ingresos_por_tipo(hoy.month, hoy.year)

    # 5. Pagos Rechazados (Registro y Auditoría)
    pagos_rechazados_mes = Pago.objects.filter(
        estado=Pago.EstadoPago.RECHAZADO,
        fecha_registro__month=hoy.month,
        fecha_registro__year=hoy.year
    )
    total_rechazados_monto = pagos_rechazados_mes.aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
    pagos_rechazados_recientes = pagos_rechazados_mes.order_by('-fecha_registro')[:10]

    pagos_pendientes = Pago.objects.filter(estado=Pago.EstadoPago.PENDIENTE).order_by('-fecha_registro')
    pedidos_pendientes = Pedido.objects.filter(estado=Pedido.Estado.PENDIENTE).order_by('-fecha_registro').prefetch_related('items__producto')
    
    return render(request, 'ventas/gestion_tesoreria.html', {
        'pagos_pendientes': pagos_pendientes,
        'pedidos_pendientes': pedidos_pendientes,
        'pagos_rechazados_recientes': pagos_rechazados_recientes,
        'ingresos_por_actividad': ingresos_por_actividad,
        'stats_tipos': stats_tipos,
        'kpis': {
            'ingresos_mes': ingresos_totales_mes,
            'ingresos_tienda': ingresos_pedidos,
            'ingresos_pagos': ingresos_pagos,
            'pendientes_count': pendientes_count,
            'pendientes_monto': pendientes_monto,
            'rechazados_monto': total_rechazados_monto,
            'rechazados_count': pagos_rechazados_mes.count(),
        },
        'chart_data': {
            'labels': chart_labels,
            'values': chart_values,
            'metodos_labels': metodos_labels,
            'metodos_values': metodos_values,
        },
        'cierres_recientes': CierreCaja.objects.all()[:12]
    })

@profe_requerido
def exportar_tesoreria_csv(request):
    """ Genera un reporte CSV de los pagos aprobados del mes actual (Sprint 12). """
    if not request.user_obj.rol_gestion_tesoreria and not request.user_obj.rol_acceso_total:
        return HttpResponse("No autorizado", status=403)

    hoy = timezone.now().date()
    pagos = Pago.objects.filter(
        estado=Pago.EstadoPago.APROBADO,
        fecha_registro__month=hoy.month,
        fecha_registro__year=hoy.year
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
def generar_pdf_tesoreria(mes, anio):
    """ Lógica interna para construir el PDF (reutilizable). """
    pagos = Pago.objects.filter(
        estado=Pago.EstadoPago.APROBADO,
        fecha_registro__month=mes,
        fecha_registro__year=anio
    ).select_related('alumno')

    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    hoy = timezone.now()

    # Marca de Agua (Watermark institutional)
    try:
        import os
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'Logo Long Hu He Transparent.png')
        if os.path.exists(logo_path):
            p.saveState()
            p.setFillAlpha(0.08)
            img_w, img_h = 15*cm, 15*cm
            p.drawImage(logo_path, (width-img_w)/2, (height-img_h)/2, width=img_w, height=img_h, mask='auto')
            p.restoreState()
    except Exception as e:
        print(f"Error marcas de agua: {e}")

    # Cabecera
    # Determinar nombre del mes para el título
    nombres_meses = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio', 
                     7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}
    mes_nombre = nombres_meses.get(mes, str(mes))
    
    p.setFont("Helvetica-Bold", 16)
    p.drawString(2*cm, height - 2*cm, "Cierre de Caja Mensual - Long Hu He")
    p.setFont("Helvetica", 10)
    p.drawString(2*cm, height - 2.5*cm, f"Período: {mes_nombre} {anio} | Generado el: {hoy.strftime('%d/%m/%Y')}")
    
    # Tabla simple
    y = height - 4*cm
    p.setFont("Helvetica-Bold", 10)
    p.drawString(2*cm, y, "Fecha")
    p.drawString(5*cm, y, "Alumno")
    p.drawString(11*cm, y, "Método")
    p.drawString(15*cm, y, "Monto")
    
    y -= 0.5*cm
    p.line(2*cm, y, width - 2*cm, y)
    y -= 0.5*cm
    
    total = Decimal('0.00')
    p.setFont("Helvetica", 9)
    for pago in pagos:
        if y < 3*cm: # Nueva página
            p.showPage()
            y = height - 2*cm
            p.setFont("Helvetica-Bold", 10)
            p.drawString(2*cm, y, "Fecha")
            p.drawString(5*cm, y, "Alumno")
            p.drawString(11*cm, y, "Método")
            p.drawString(15*cm, y, "Monto")
            y -= 0.5*cm
            p.line(2*cm, y, width - 2*cm, y)
            y -= 0.5*cm
            p.setFont("Helvetica", 9)

        p.drawString(2*cm, y, pago.fecha_registro.strftime("%d/%m/%y"))
        p.drawString(5*cm, y, str(pago.alumno.nombre_completo)[:30])
        p.drawString(11*cm, y, pago.get_metodo_display())
        p.drawString(15*cm, y, f"$ {pago.monto}")
        total += pago.monto
        y -= 0.5*cm

    y -= 1*cm
    p.line(2*cm, y+0.5*cm, width-2*cm, y+0.5*cm)
    p.setFont("Helvetica-Bold", 12)
    p.drawString(11*cm, y, "TOTAL INGRESOS:")
    p.drawString(15*cm, y, f"$ {total}")

    p.showPage()
    p.save()

    buffer.seek(0)
    return buffer

@profe_requerido
def exportar_tesoreria_pdf(request):
    """ Descarga el PDF del mes actual sin cerrar la caja. """
    if not request.user_obj.rol_gestion_tesoreria and not request.user_obj.rol_acceso_total:
        return HttpResponse("No autorizado", status=403)
    
    from .services.tesoreria_service import TesoreriaService
    hoy = timezone.now()
    buffer = TesoreriaService.generar_pdf_tesoreria(hoy.month, hoy.year)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="reporte_tesoreria_{hoy.strftime("%Y_%m")}.pdf"'
    return response

@profe_requerido
@requiere_rol('rol_gestion_tesoreria')
def cerrar_caja_mensual(request):
    """ Genera el PDF, lo guarda en el historial y 'cierra' el mes usando TesoreriaService. """
    from .services.tesoreria_service import TesoreriaService
    from apps.usuarios.models import BitacoraSeguridad
    try:
        cierre = TesoreriaService.cerrar_mes(request.user_obj)
        BitacoraSeguridad.registrar(request, BitacoraSeguridad.TipoEvento.CIERRE_CAJA, f"Cierre de caja manual mes {cierre.mes}/{cierre.anio} por ${cierre.total_recaudado}")
        messages.success(request, "Cierre de caja guardado con éxito.")
    except ValueError as e:
        messages.warning(request, str(e))
        
    return redirect('gestion_tesoreria')

@profe_requerido
def gestionar_pago_accion(request, pago_id):
    """ Procesa la aprobacion o rechazo de un pago manual usando PagoService. """
    pago = get_object_or_404(Pago.objects.select_for_update(), id=pago_id)
    if request.method == 'POST':
        accion = request.POST.get('accion')
        motivo = request.POST.get('motivo', '')
        
        from .services.pago_service import PagoService
        if accion == 'aprobar':
            PagoService.transicionar_a_aprobado(pago)
            messages.success(request, f"Pago de {pago.alumno.nombre} aprobado y procesado.")
        elif accion == 'rechazar':
            pago.estado = Pago.EstadoPago.RECHAZADO
            pago.motivo_rechazo = motivo
            pago.save()
            messages.warning(request, "Pago rechazado.")
            
    return redirect('gestion_tesoreria')

@profe_requerido
def gestionar_pedido_accion(request, pedido_id):
    """ Procesa el pago o cancelación de un pedido usando PedidoService. """
    pedido = get_object_or_404(Pedido.objects.select_for_update(), id=pedido_id)
    if not request.user_obj.rol_gestion_tesoreria and not request.user_obj.rol_acceso_total:
        return HttpResponse("No autorizado", status=403)
        
    if request.method == 'POST':
        accion = request.POST.get('accion')
        from .services.pedido_service import PedidoService
        if accion == 'pagar':
            PedidoService.transicionar_a_pagado(pedido)
            messages.success(request, f"Pedido #{pedido.id} pagado y stock actualizado.")
        elif accion == 'entregar':
            PedidoService.transicionar_a_entregado(pedido)
            messages.success(request, f"Pedido #{pedido.id} entregado.")
        elif accion == 'cancelar':
            PedidoService.transicionar_a_cancelado(pedido)
            messages.warning(request, f"Pedido #{pedido.id} cancelado y stock restaurado.")
            
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
            activity_obj = get_object_or_404(Actividad, id=pago_data['actividad'])
            
            from .services.pago_service import PagoService
            pago = PagoService.registrar_pago(
                alumno=alumno,
                actividad=activity_obj,
                tipo=pago_data['tipo'],
                metodo=pago_data.get('metodo') or pago_data.get('método'),
                comprobante=request.FILES.get('comprobante'),
                cantidad_clases=pago_data.get('cantidad_clases')
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
            from .services.pago_service import PagoService
            pago = PagoService.registrar_pago(
                alumno=alumno,
                actividad_id=actividad.id,
                tipo=pago_data['tipo'],
                metodo=pago_data.get('metodo') or pago_data.get('método'),
                descuento_id=pago_data.get('descuento_id'),
                cantidad_clases=pago_data.get('cantidad_clases')
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
    gateway = PaymentGatewayFactory.get_gateway(custom_access_token=access_token)
    try:
        init_point, preference_id = gateway.crear_preferencia(pago)
        if preference_id:
            pago.mercado_pago_id = preference_id
            pago.save(update_fields=['mercado_pago_id'])
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
                
                gateway = PaymentGatewayFactory.get_gateway(custom_access_token=access_token)
                payment_info = gateway.obtener_pago(resource_id)
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
                                from apps.ventas.services.pedido_service import PedidoService
                                PedidoService.transicionar_a_pagado(pedido)
                            else:
                                pedido.save()
                    else:
                        # LOCK del Pago para procesar secuencialmente
                        pago = Pago.objects.select_for_update().filter(id=external_ref).first()
                        if pago and pago.estado != Pago.EstadoPago.APROBADO:
                            pago.mercado_pago_status = status
                            pago.mercado_pago_id = resource_id
                            if status in ("accredited", "approved"):
                                from apps.ventas.services.pago_service import PagoService
                                PagoService.transicionar_a_aprobado(pago)
                            else:
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
        from apps.ventas.services.tienda_service import TiendaService
        
        pedido, error_msg = TiendaService.crear_pedido_directo(
            alumno=alumno, producto=producto, cantidad=cantidad, metodo_pago=metodo_pago
        )
        
        if error_msg:
            messages.error(request, error_msg)
            return redirect('tienda_inicio')

        if metodo_pago == Pago.MetodoPago.MERCADOPAGO:
            from apps.ventas.services.payments.factory import PaymentGatewayFactory
            mp_strategy = PaymentGatewayFactory.get_gateway('mercadopago')
            pref_url = mp_strategy.crear_preferencia(
                titulo=f"Tienda LongHuHe: {producto.nombre} x{cantidad}",
                precio=float(pedido.total),
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
