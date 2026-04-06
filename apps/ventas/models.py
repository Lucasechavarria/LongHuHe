from django.db import models
from django.core.exceptions import ValidationError
from apps.usuarios.models import Usuario
from apps.academia.models import Actividad, Cronograma

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
        on_delete=models.CASCADE,
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
    monto_comision_profesor = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    monto_utilidad_asociacion = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
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
        """ Calcula cuanto va para el profe y cuanto para la asociacion. """
        if not self.monto:
            return
        
        if self.clase_programada:
            self.clase_programada.profesor
        
        pct = 0
        if self.actividad and hasattr(self.actividad, 'precio_mes'):
            pct = 50 # Simplificado: 50% para el profe por defecto si no hay mas info
            # En la vida real usariamos un campo 'porcentaje_comision' en Actividad o Usuario
        
        self.monto_comision_profesor = self.monto * (pct / 100)
        self.monto_utilidad_asociacion = self.monto - self.monto_comision_profesor

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        old_estado = None
        if not is_new:
            try:
                old_pago = Pago.objects.get(pk=self.pk)
                old_estado = old_pago.estado
            except Pago.DoesNotExist:
                pass

        # Auto-asignar monto si falta, basado en la actividad
        if not self.monto and self.actividad:
            if self.tipo == self.TipoPago.MES:
                self.monto = self.actividad.precio_mes
            elif self.tipo == self.TipoPago.CLASE_SUELTA:
                self.monto = self.actividad.precio_clase
            elif self.tipo == self.TipoPago.PAQUETE:
                self.monto = self.actividad.precio_clase * (self.cantidad_clases or 1)

        ha_sido_aprobado = (is_new and self.estado == self.EstadoPago.APROBADO) or (old_estado != self.EstadoPago.APROBADO and self.estado == self.EstadoPago.APROBADO)

        if ha_sido_aprobado:
            if self.monto_comision_profesor == 0:
                self.recalcular_comisiones()
            
            # Lógica de Vencimiento / Expiración
            from datetime import date
            hoy = date.today()
            alumno = self.alumno
            
            if self.tipo == self.TipoPago.MES:
                vencimiento_actual = alumno.fecha_vencimiento_cuota
                mes_prox = hoy.month % 12 + 1
                anio_prox = hoy.year + (1 if hoy.month == 12 else 0)
                
                # Respetar el día de vencimiento cíclico
                dia_corte = vencimiento_actual.day if vencimiento_actual else hoy.day
                
                try:
                    nuevo_vencimiento = date(anio_prox, mes_prox, dia_corte)
                except ValueError:
                    # En caso de febrero 29 u otros dias q no existan en el prox mes
                    nuevo_vencimiento = date(anio_prox, mes_prox, 28)
                
                alumno.fecha_vencimiento_cuota = nuevo_vencimiento
                alumno.fecha_prorroga = None # al pagar desaparece la prorroga
                alumno.save(update_fields=['fecha_vencimiento_cuota', 'fecha_prorroga'])

            elif self.tipo in [self.TipoPago.PAQUETE, self.TipoPago.CLASE_SUELTA]:
                # La clase suelta funciona como un paquete de 1
                clases_asumar = self.cantidad_clases or (1 if self.tipo == self.TipoPago.CLASE_SUELTA else 0)
                alumno.clases_disponibles += clases_asumar
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
        ENTREGADO = "entregado", "Entregado"
        CANCELADO = "cancelado", "Cancelado"

    alumno = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="pedidos_tienda")
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

    def descontar_stock(self):
        """ Reduce el inventario al entregar el producto """
        if self.stock_descontado:
            return
        for item in self.items.all():
            if item.variante:
                item.variante.stock -= item.cantidad
                item.variante.save()
            else:
                item.producto.stock -= item.cantidad
                item.producto.save()
        self.stock_descontado = True
        self.save()

    def restaurar_stock(self):
        """ Devuelve el inventario si se cancela un pedido entregado """
        if not self.stock_descontado:
            return
        for item in self.items.all():
            if item.variante:
                item.variante.stock += item.cantidad
                item.variante.save()
            else:
                item.producto.stock += item.cantidad
                item.producto.save()
        self.stock_descontado = False
        self.save()

    def save(self, *args, **kwargs):
        # Al pasar a ENTREGADO, descontamos automáticamente
        if self.estado == self.Estado.ENTREGADO and not self.stock_descontado:
            # Solo podemos descontar si el pedido ya existe en la DB (para tener items)
            if self.pk:
                self.descontar_stock()
        
        # Al pasar a CANCELADO, restauramos automáticamente si se había descontado
        if self.estado == self.Estado.CANCELADO and self.stock_descontado:
            self.restaurar_stock()
        
        if self.estado == self.Estado.PAGADO:
            total_costo = 0
            if self.pk:
                for item in self.items.all():
                    total_costo += (item.producto.costo_reposicion * item.cantidad)
            self.monto_costo_reposicion = total_costo
            self.monto_comision = self.total * (self.porcentaje_comision / 100)
            
            if self.clase_origen and self.clase_origen.profesor_asistente:
                pct_asistente = self.clase_origen.porcentaje_comision_asistente
                self.monto_comision_asistente = self.total * (pct_asistente / 100)
            else:
                self.monto_comision_asistente = 0
            
            self.utilidad_neta_asociacion = (
                self.total - self.monto_costo_reposicion - 
                self.monto_comision - self.monto_comision_asistente
            )
        super().save(*args, **kwargs)

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
