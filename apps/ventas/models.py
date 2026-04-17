from django.db import models
from django.core.exceptions import ValidationError
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from django.utils import timezone
from decimal import Decimal, ROUND_HALF_UP
from apps.usuarios.models import Usuario
from apps.academia.models import Actividad, Cronograma


class Descuento(models.Model):
    """
    Cupones y reglas de descuento aplicables a los pagos de cuota.
    Admite porcentaje o monto fijo, código de cupón, límite de usos y vencimiento.
    Ejemplos: 'Hermanos 20%', 'Descuento Familiar $2000', 'Promo Septiembre'.
    """

    class TipoDescuento(models.TextChoices):
        PORCENTAJE = "porcentaje", "Porcentaje (%)"
        MONTO_FIJO = "monto_fijo", "Monto Fijo ($)"

    class AplicableA(models.TextChoices):
        TODOS = "todos", "Todos los tipos de pago"
        CUOTA_MENSUAL = "cuota_mensual", "Solo Cuota Mensual"
        CLASE_SUELTA = "clase_suelta", "Solo Clase Suelta"
        PAQUETE = "paquete", "Solo Paquete de Clases"

    nombre = models.CharField(
        max_length=150,
        help_text="Nombre descriptivo, ej: 'Descuento Hermanos 20%' o 'Beca Parcial Familia García'."
    )
    descripcion = models.TextField(
        "Descripción / Nota Interna", blank=True, default="",
        help_text="Razón del descuento, condiciones, etc."
    )
    tipo = models.CharField(
        "Tipo de Descuento", max_length=20, choices=TipoDescuento.choices,
        default=TipoDescuento.PORCENTAJE
    )
    valor = models.DecimalField(
        "Valor del Descuento", max_digits=10, decimal_places=2,
        help_text="Si es porcentaje: ingresá 20 para 20%. Si es monto fijo: ingresá 1500 para $1.500."
    )
    codigo = models.CharField(
        "Código de Cupón", max_length=50, blank=True, default="", unique=False, db_index=True,
        help_text="Opcional. Si se completa, el descuento sólo se aplica cuando se ingresa este código. Ej: HERMANOS, FAMILIA2025."
    )
    activo = models.BooleanField(
        default=True,
        help_text="Desactiválo temporalmente sin borrar el historial."
    )
    usos_maximos = models.PositiveIntegerField(
        "Máximo de Usos", null=True, blank=True,
        help_text="Dejá vacío para usos ilimitados."
    )
    usos_actuales = models.PositiveIntegerField(
        "Usos Actuales", default=0, editable=False
    )
    fecha_vencimiento = models.DateField(
        "Fecha de Vencimiento", null=True, blank=True,
        help_text="Dejá vacío si no vence nunca."
    )
    monto_minimo_pago = models.DecimalField(
        "Monto Mínimo de Pago", max_digits=10, decimal_places=2, default=0,
        help_text="El cupón solo será aplicable si el total es igual o superior a este monto."
    )
    monto_maximo_descuento = models.DecimalField(
        "Tope Máximo de Descuento", max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="Para descuentos porcentuales, este es el monto máximo que se restará (ej: 50% con tope de $1.000)."
    )
    aplicable_a = models.CharField(
        "Aplicable a", max_length=20, choices=AplicableA.choices,
        default=AplicableA.TODOS
    )

    class Meta:
        verbose_name = "Descuento / Cupón"
        verbose_name_plural = "02.4 - Descuentos y Cupones"
        ordering = ["nombre"]
        db_table = 'core_descuento'
        constraints = [
            models.UniqueConstraint(
                fields=['codigo'], 
                condition=models.Q(activo=True),
                name='unique_active_discount_code'
            )
        ]

    def __str__(self):
        if self.tipo == self.TipoDescuento.PORCENTAJE:
            return f"{self.nombre} ({self.valor}%)"
        return f"{self.nombre} (${self.valor})"

    @property
    def esta_vigente(self):
        """Retorna True si el descuento puede usarse hoy."""
        if not self.activo:
            return False
        if self.usos_maximos is not None and self.usos_actuales >= self.usos_maximos:
            return False
        if self.fecha_vencimiento and timezone.now().date() > self.fecha_vencimiento:
            return False
        return True

    def calcular_descuento(self, monto_base):
        """Calcula el monto a descontar sobre un monto base dado, respetando el tope máximo."""
        
        # Validar monto mínimo
        if self.monto_minimo_pago and monto_base < self.monto_minimo_pago:
            return Decimal('0.00')

        if self.tipo == self.TipoDescuento.PORCENTAJE:
            desc = (monto_base * self.valor / Decimal('100')).quantize(Decimal('0.01'))
            if self.monto_maximo_descuento and desc > self.monto_maximo_descuento:
                return self.monto_maximo_descuento
            return desc
        
        monto_final = min(self.valor, monto_base)  # No descontar más de lo que vale
        return monto_final

class Pago(models.Model):
    """
    Aviso de pago generado por el alumno.
    """
    class TipoPago(models.TextChoices):
        MES = "mes", "Mes Completo"
        CLASE_SUELTA = "clase_suelta", "1 Clase"
        PAQUETE = "paquete", "Paquete de Clases"

    class MetodoPago(models.TextChoices):
        TRANSFERENCIA = "transferencia", "Transferencia Bancaria"
        MERCADOPAGO = "mercadopago", "Mercado Pago"
        EFECTIVO = "efectivo", "En Efectivo"

    class EstadoPago(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APROBADO = "approved", "Aprobado" # Matches MP 'approved'
        RECHAZADO = "rejected", "Rechazado"

    alumno = models.ForeignKey(
        Usuario,
        on_delete=models.PROTECT,
        related_name="pagos",
    )
    actividad = models.ForeignKey(
        Actividad,
        on_delete=models.CASCADE,
        related_name="pagos",
        null=True
    )
    clase_programada = models.ForeignKey(
        Cronograma,
        on_delete=models.SET_NULL,
        related_name="pagos",
        null=True,
        blank=True,
    )
    monto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    monto_original = models.DecimalField(
        "Monto Original (sin descuento)", max_digits=10, decimal_places=2, default=0,
        help_text="Precio base antes de aplicar cualquier descuento. Referencia inmutable."
    )
    monto_comision_profesor = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    monto_utilidad_asociacion = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # --- DESCUENTOS (solo aplican a Cuota Mensual) ---
    descuento = models.ForeignKey(
        Descuento,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="pagos_con_descuento",
        verbose_name="Descuento Aplicado",
        help_text="Solo válido para pagos de tipo Mes Completo."
    )
    monto_descuento = models.DecimalField(
        "Monto Descontado", max_digits=10, decimal_places=2, default=0,
        help_text="Calculado automáticamente al guardar según el descuento seleccionado."
    )

    motivo_rechazo = models.TextField(blank=True, null=True)
    fecha_pago_real = models.DateField(null=True, blank=True)

    tipo = models.CharField(max_length=20, choices=TipoPago.choices)
    cantidad_clases = models.IntegerField(null=True, blank=True)
    metodo = models.CharField(max_length=20, choices=MetodoPago.choices)
    comprobante = models.FileField(
        upload_to="comprobantes/",
        null=True,
        blank=True,
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoPago.choices,
        default=EstadoPago.PENDIENTE,
    )
    mercado_pago_id = models.CharField(max_length=255, null=True, blank=True)
    mercado_pago_status = models.CharField(max_length=50, null=True, blank=True)
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Pago / Finanzas"
        verbose_name_plural = "02.3 - Pagos y Tesorería"
        ordering = ["-fecha_registro"]
        db_table = 'core_pago'

    def __str__(self):
        try:
            fecha = self.fecha_registro.strftime("%d/%m/%Y %H:%M") if self.fecha_registro else "Sin Fecha"
            alumno_str = self.alumno.nombre_completo if self.alumno else "Alumno desconocido"
            tipo_str = self.get_tipo_display()
            estado_str = self.get_estado_display()
            return f"Pago de {alumno_str} - {tipo_str} - {estado_str} - {fecha}"
        except Exception:
            return f"Pago #{self.id}"

    def recalcular_comisiones(self):
        """ Calcula cuanto va para el profe y cuanto para la asociacion basado en la clase. """
        if not self.monto:
            return
        
        # 1. Determinar el porcentaje
        from decimal import Decimal
        pct = Decimal('50.00') # Default base: 50%
        
        if self.clase_programada:
            pct = self.clase_programada.porcentaje_comision_profesor
        elif self.actividad and hasattr(self.actividad, 'porcentaje_comision'):
            # En caso de que se agregue comision a nivel actividad en el futuro
            pct = self.actividad.porcentaje_comision
        
        # 2. Calcular montos
        self.monto_comision_profesor = (self.monto * (pct / Decimal('100'))).quantize(Decimal('0.01'))
        self.monto_utilidad_asociacion = self.monto - self.monto_comision_profesor

    def save(self, *args, **kwargs):
        from decimal import Decimal
        from django.db import transaction
        with transaction.atomic():
            is_new = self.pk is None
            old_estado = None

            if not is_new:
                try:
                    old_pago = Pago.objects.get(pk=self.pk)
                    old_estado = old_pago.estado
                except Pago.DoesNotExist:
                    pass

            # 1. Auto-asignar monto base desde la actividad (solo en creación)
            if not self.monto and self.actividad:
                if self.tipo == self.TipoPago.MES:
                    self.monto = self.actividad.precio_mes
                elif self.tipo == self.TipoPago.CLASE_SUELTA:
                    self.monto = self.actividad.precio_clase
                elif self.tipo == self.TipoPago.PAQUETE:
                    self.monto = self.actividad.precio_clase * (self.cantidad_clases or 1)

            # 2. Guardar el monto original si todavía no está registrado
            if not self.monto_original and self.monto:
                self.monto_original = self.monto

            # 3. Aplicar Descuento — SOLO para Cuota Mensual
            if self.descuento_id and self.tipo == self.TipoPago.MES and self.monto_original:
                descuento_obj = self.descuento
                self.monto_descuento = descuento_obj.calcular_descuento(self.monto_original)
                self.monto = self.monto_original - self.monto_descuento
            else:
                if self.tipo != self.TipoPago.MES:
                    self.descuento = None
                self.monto_descuento = Decimal('0')
                if self.monto_original:
                    self.monto = self.monto_original

            # 4. Detectar si este save representa la primera aprobación
            ha_sido_aprobado = (
                (is_new and self.estado == self.EstadoPago.APROBADO) or
                (old_estado != self.EstadoPago.APROBADO and self.estado == self.EstadoPago.APROBADO)
            )

            if ha_sido_aprobado:
                # 4a. Calcular comisiones del profesor
                if self.monto_comision_profesor == 0:
                    self.recalcular_comisiones()

                # 4b. Incrementar contador de usos del descuento (solo 1 vez al aprobar)
                if self.descuento_id and self.tipo == self.TipoPago.MES:
                    Descuento.objects.filter(pk=self.descuento_id).update(
                        usos_actuales=models.F('usos_actuales') + 1
                    )

                # 4c. Lógica de Vencimiento Cíclico
                from datetime import date
                hoy = date.today()
                alumno = self.alumno

                if self.tipo == self.TipoPago.MES:
                    if not alumno.dia_corte_cuota:
                        alumno.dia_corte_cuota = hoy.day

                    dia_corte = alumno.dia_corte_cuota
                    base = alumno.fecha_vencimiento_cuota if (alumno.fecha_vencimiento_cuota and alumno.fecha_vencimiento_cuota >= hoy) else hoy
                    mes_sig = base.month % 12 + 1
                    anio_sig = base.year + (1 if base.month == 12 else 0)

                    import calendar
                    ultimo_dia_mes_sig = calendar.monthrange(anio_sig, mes_sig)[1]
                    dia_real = min(dia_corte, ultimo_dia_mes_sig)

                    nuevo_vencimiento = date(anio_sig, mes_sig, dia_real)

                    alumno.fecha_vencimiento_cuota = nuevo_vencimiento
                    alumno.fecha_prorroga = None
                    alumno.save(update_fields=['fecha_vencimiento_cuota', 'fecha_prorroga', 'dia_corte_cuota'])

                elif self.tipo in [self.TipoPago.PAQUETE, self.TipoPago.CLASE_SUELTA]:
                    clases_a_sumar = self.cantidad_clases or (1 if self.tipo == self.TipoPago.CLASE_SUELTA else 0)
                    alumno.clases_disponibles = models.F('clases_disponibles') + clases_a_sumar
                    alumno.save(update_fields=['clases_disponibles'])

            super().save(*args, **kwargs)

    def clean(self):
        errores = {}
        if self.tipo == self.TipoPago.PAQUETE:
            if not self.cantidad_clases or self.cantidad_clases <= 0:
                errores["cantidad_clases"] = "Debes indicar cuántas clases incluye el paquete."
        if self.metodo == self.MetodoPago.TRANSFERENCIA and not self.comprobante:
            errores["comprobante"] = "Debes adjuntar el comprobante para pagos por transferencia."
        if errores:
            raise ValidationError(errores)

class CategoriaProducto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = "Producto: Categoría"
        verbose_name_plural = "04.2 - Tienda: Categorías (Configuración)"
        ordering = ["nombre"]
        db_table = 'core_categoriaproducto'

    def __str__(self):
        return self.nombre

class Producto(models.Model):
    categoria = models.ForeignKey(CategoriaProducto, on_delete=models.CASCADE, related_name="productos")
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    activo = models.BooleanField(default=True)
    permite_backorder = models.BooleanField(default=False)
    
    cuotas_maximas = models.IntegerField("Cuotas Máximas", default=1)
    costo_reposicion = models.DecimalField(
        "Costo de Reposición", max_digits=10, decimal_places=2, default=0
    )
    porcentaje_comision = models.DecimalField(
        "Porcentaje de Comisión Profe", max_digits=5, decimal_places=2, default=0
    )
    
    stock = models.IntegerField("Stock Global (si no hay variantes)", default=0)
    monto_reserva = models.DecimalField(
        "Monto de Reserva (Seña)", max_digits=10, decimal_places=2, default=0,
        help_text="Monto mínimo para encargar el producto si no se paga el total."
    )
    
    foto1 = models.ImageField(upload_to="tienda/", blank=True, null=True)
    foto2 = models.ImageField(upload_to="tienda/", blank=True, null=True)
    foto3 = models.ImageField(upload_to="tienda/", blank=True, null=True)
    foto4 = models.ImageField(upload_to="tienda/", blank=True, null=True)
    foto5 = models.ImageField(upload_to="tienda/", blank=True, null=True)

    def save(self, *args, **kwargs):
        # Lógica de optimización de imágenes (WebP)
        # Evitamos recursion infinita manejando la bandera 'img_optimized'
        if not getattr(self, '_img_optimized', False):
            from PIL import Image
            import io
            from django.core.files.base import ContentFile
            
            for i in range(1, 6):
                attr = f'foto{i}'
                img_file = getattr(self, attr)
                if img_file and not img_file.name.endswith('.webp'):
                    try:
                        img = Image.open(img_file)
                        if img.mode in ("RGBA", "P"):
                            img = img.convert("RGB")
                        thumb_io = io.BytesIO()
                        img.save(thumb_io, 'WEBP', quality=85)
                        new_name = img_file.name.split('.')[0] + '.webp'
                        getattr(self, attr).save(new_name, ContentFile(thumb_io.getvalue()), save=False)
                    except Exception:
                        pass
            self._img_optimized = True
            
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = "Producto: Ficha Central"
        verbose_name_plural = "04.1 - Tienda: Productos"
        ordering = ["nombre"]
        db_table = 'core_producto'

    def __str__(self):
        return self.nombre

    @property
    def hay_stock(self):
        if self.variantes.exists():
            return self.variantes.filter(stock__gt=0).exists()
        return self.stock > 0

class ProductoVariante(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="variantes")
    talle = models.CharField(max_length=50)
    stock = models.IntegerField("Cantidad en Stock", default=0)

    class Meta:
        verbose_name = "Variante de Producto (Talle)"
        verbose_name_plural = "Variantes de Producto (Talles)"
        db_table = 'core_productovariante'

    def __str__(self):
        return f"{self.producto.nombre} - Talle: {self.talle}"

class Pedido(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente de Pago/Conf"
        PAGADO = "pagado", "Pagado - A Preparar"
        RESERVADO = "reservado", "Reservado / Señado"
        ENTREGADO = "entregado", "Entregado"
        CANCELADO = "cancelado", "Cancelado"

    alumno = models.ForeignKey(Usuario, on_delete=models.PROTECT, related_name="pedidos_tienda")
    fecha_registro = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    metodo_pago = models.CharField(max_length=20, choices=Pago.MetodoPago.choices)
    cuotas = models.IntegerField(default=1)
    comprobante = models.FileField(upload_to="comprobantes_pedidos/", blank=True, null=True)
    
    mercado_pago_id = models.CharField(max_length=255, null=True, blank=True)
    mercado_pago_status = models.CharField(max_length=50, null=True, blank=True)
    
    profesor_venta = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True, 
        related_name="ventas_tienda_generadas",
        limit_choices_to={'es_profe': True}
    )
    porcentaje_comision = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    monto_comision = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    clase_origen = models.ForeignKey(
        Cronograma, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="pedidos_clase"
    )
    
    monto_costo_reposicion = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    monto_comision_asistente = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    utilidad_neta_asociacion = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    backorder = models.BooleanField(default=False)
    stock_descontado = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Tienda: Pedido"
        verbose_name_plural = "04.3 - Tienda: Gestión de Pedidos"
        ordering = ["-fecha_registro"]
        db_table = 'core_pedido'

    def __str__(self):
        try:
            alumno_str = self.alumno.nombre_completo if self.alumno else "Alumno desconocido"
            return f"Pedido #{self.id} - {alumno_str}"
        except Exception:
            return f"Pedido #{self.id}"

    def descontar_stock(self, logic_only=False):
        """ Reduce el inventario al entregar el producto """
        if self.stock_descontado:
            return
        
        from django.db.models import F
        for item in self.items.all():
            if item.variante:
                item.variante.stock = F('stock') - item.cantidad
                item.variante.save(update_fields=['stock'])
            else:
                item.producto.stock = F('stock') - item.cantidad
                item.producto.save(update_fields=['stock'])
        
        self.stock_descontado = True
        if not logic_only:
            self.save(update_fields=['stock_descontado'])

    def restaurar_stock(self, logic_only=False):
        """ Devuelve el inventario si se cancela un pedido entregado """
        if not self.stock_descontado:
            return
            
        from django.db.models import F
        for item in self.items.all():
            if item.variante:
                item.variante.stock = F('stock') + item.cantidad
                item.variante.save(update_fields=['stock'])
            else:
                item.producto.stock = F('stock') + item.cantidad
                item.producto.save(update_fields=['stock'])
        
        self.stock_descontado = False
        if not logic_only:
            self.save(update_fields=['stock_descontado'])

    def recalcular_stats(self, logic_only=False):
        """ Recalcula costos de reposición y utilidad basándose en los items actuales. """
        if self.estado in [self.Estado.PAGADO, self.Estado.RESERVADO, self.Estado.ENTREGADO]:
            total_costo = Decimal('0.00')
            for item in self.items.all():
                costo_item = (Decimal(str(item.producto.costo_reposicion)) * item.cantidad)
                total_costo += costo_item
            
            self.monto_costo_reposicion = total_costo.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            # Recalcular porcentajes
            pct_comision = Decimal(str(self.porcentaje_comision)) / Decimal('100')
            self.monto_comision = (self.total * pct_comision).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            if self.clase_origen and self.clase_origen.profesor_asistente:
                pct_asistente = Decimal(str(self.clase_origen.porcentaje_comision_asistente)) / Decimal('100')
                self.monto_comision_asistente = (self.total * pct_asistente).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            else:
                self.monto_comision_asistente = Decimal('0.00')
            
            self.utilidad_neta_asociacion = (
                self.total - self.monto_costo_reposicion - 
                self.monto_comision - self.monto_comision_asistente
            ).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
            
            if not logic_only:
                super().save(update_fields=[
                    'monto_costo_reposicion', 'monto_comision', 
                    'monto_comision_asistente', 'utilidad_neta_asociacion'
                ])

    def save(self, *args, **kwargs):
        # 1. Detectar cambios de estado críticos para stock
        if self.pk:
            # Descontamos stock si el pedido se paga o se entrega (y no se ha descontado ya)
            if self.estado in [self.Estado.PAGADO, self.Estado.ENTREGADO] and not self.stock_descontado:
                self.descontar_stock(logic_only=True)
            # Restauramos stock si se cancela y estaba descontado
            if self.estado == self.Estado.CANCELADO and self.stock_descontado:
                self.restaurar_stock(logic_only=True)
        
        # 2. Guardado inicial / actualización de campos base
        super().save(*args, **kwargs)
        
        # 3. Disparar recalcular si ya tiene items (o llamarlo desde el signal post_save de los items)
        if self.pk:
            self.recalcular_stats(logic_only=False)



class PedidoItem(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey(Producto, on_delete=models.RESTRICT)
    variante = models.ForeignKey(ProductoVariante, on_delete=models.SET_NULL, null=True, blank=True)
    cantidad = models.IntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Item de Pedido"
        verbose_name_plural = "Items de Pedido"
        db_table = 'core_pedidoitem'

    def __str__(self):
        return f"{self.cantidad}x {self.producto.nombre}"

@receiver(post_save, sender=PedidoItem)
@receiver(post_delete, sender=PedidoItem)
def actualizar_pedido_on_item_change(sender, instance, **kwargs):
    """ Fuerza la recalculación del pedido cuando sus items cambian. """
    if instance.pedido:
        instance.pedido.recalcular_stats()

# ==========================================
# SEÑALES DE LIMPIEZA DE ALMACENAMIENTO (S3)
# ==========================================

def borrar_archivo_si_existe(archivo):
    """Auxiliar para borrar archivos físicos de almacenamiento."""
    if archivo and hasattr(archivo, 'delete'):
        try:
            archivo.delete(save=False)
        except Exception:
            pass # No bloqueamos el flujo si el archivo no existe en el storage

# --- Limpiar imagenes de Producto ---
@receiver(post_delete, sender=Producto)
def auto_delete_file_on_delete_prod(sender, instance, **kwargs):
    for i in range(1, 6):
        borrar_archivo_si_existe(getattr(instance, f'foto{i}', None))

@receiver(pre_save, sender=Producto)
def auto_delete_file_on_change_prod(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old_obj = Producto.objects.get(pk=instance.pk)
    except Producto.DoesNotExist:
        return

    for i in range(1, 6):
        attr = f'foto{i}'
        old_file = getattr(old_obj, attr)
        new_file = getattr(instance, attr)
        if old_file and old_file != new_file:
            borrar_archivo_si_existe(old_file)

# --- Limpiar comprobantes de Pago y Pedido ---
@receiver(post_delete, sender=Pago)
def auto_delete_comprobante_pago_on_delete(sender, instance, **kwargs):
    borrar_archivo_si_existe(instance.comprobante)

@receiver(pre_save, sender=Pago)
def auto_delete_comprobante_pago_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old_obj = Pago.objects.get(pk=instance.pk)
        old_file = old_obj.comprobante
        new_file = instance.comprobante
        if old_file and old_file != new_file:
            borrar_archivo_si_existe(old_file)
    except Pago.DoesNotExist:
        pass

@receiver(post_delete, sender=Pedido)
def auto_delete_comprobante_pedido_on_delete(sender, instance, **kwargs):
    borrar_archivo_si_existe(instance.comprobante)

@receiver(pre_save, sender=Pedido)
def auto_delete_comprobante_pedido_on_change(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old_obj = Pedido.objects.get(pk=instance.pk)
        old_file = old_obj.comprobante
        new_file = instance.comprobante
        if old_file and old_file != new_file:
            borrar_archivo_si_existe(old_file)
    except Pedido.DoesNotExist:
        pass
