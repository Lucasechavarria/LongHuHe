from django.contrib import admin
from django.db.models import Q
from django.utils.html import format_html
from apps.usuarios.models import Usuario
from apps.usuarios.admin import ModularAdminMixin
from .models import Pago, Pedido, CategoriaProducto, Producto, ProductoVariante, Descuento

@admin.register(Descuento)
class DescuentoAdmin(admin.ModelAdmin):
    list_display = (
        "nombre", "tipo", "valor", "codigo_display", "activo",
        "usos_display", "fecha_vencimiento", "aplicable_a", "vigencia_display"
    )
    list_filter = ("activo", "tipo", "aplicable_a")
    search_fields = ("nombre", "codigo", "descripcion")
    readonly_fields = ("usos_actuales",)
    list_editable = ("activo",)
    actions = ["activar_descuentos", "desactivar_descuentos"]

    fieldsets = (
        ("Identificación", {"fields": ("nombre", "descripcion", "codigo", "aplicable_a")}),
        ("Valor", {"fields": ("tipo", "valor")}),
        ("Control de Vigencia", {"fields": ("activo", "usos_maximos", "usos_actuales", "fecha_vencimiento")}),
    )

    @admin.display(description="Código")
    def codigo_display(self, obj):
        if obj.codigo:
            return format_html('<code style="background:#f0f0f0;padding:2px 6px;border-radius:3px;">{}</code>', obj.codigo)
        return format_html('<span style="color:#aaa;">Sin código</span>')

    @admin.display(description="Usos")
    def usos_display(self, obj):
        if obj.usos_maximos is not None:
            pct = int((obj.usos_actuales / obj.usos_maximos) * 100) if obj.usos_maximos else 0
            color = "#ef4444" if pct >= 100 else ("#f97316" if pct >= 75 else "#22c55e")
            return format_html(
                '<span style="color:{};font-weight:bold;">{} / {}</span>',
                color, obj.usos_actuales, obj.usos_maximos
            )
        return format_html('<span style="color:#6b7280;">{} / ∞</span>', obj.usos_actuales)

    @admin.display(description="Vigente?", boolean=False)
    def vigencia_display(self, obj):
        if obj.esta_vigente:
            return format_html('<span style="background:#22c55e;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;">ACTIVO</span>')
        return format_html('<span style="background:#ef4444;color:#fff;padding:2px 8px;border-radius:4px;font-size:11px;">VENCIDO/AGOTADO</span>')

    @admin.action(description="✅ Activar descuentos seleccionados")
    def activar_descuentos(self, request, queryset):
        updated = queryset.update(activo=True)
        self.message_user(request, f"{updated} descuento(s) activado(s).")

    @admin.action(description="❌ Desactivar descuentos seleccionados")
    def desactivar_descuentos(self, request, queryset):
        updated = queryset.update(activo=False)
        self.message_user(request, f"{updated} descuento(s) desactivado(s).")

    def has_module_permission(self, request):
        user = request.user
        if not user.is_authenticated:
            return False
        return user.is_superuser or getattr(user, 'rol_acceso_total', False) or getattr(user, 'rol_gestion_tesoreria', False)


@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("id", "alumno", "tipo", "cantidad_clases", "monto", "monto_descuento", "descuento", "metodo", "estado", "fecha_registro")
    list_filter = ("estado", "tipo", "fecha_registro")
    list_select_related = ("alumno", "actividad", "descuento")
    search_fields = ("alumno__nombre", "alumno__apellido", "alumno__celular", "alumno__dni")
    autocomplete_fields = ("alumno",)
    list_editable = ("cantidad_clases", "monto", "estado")
    readonly_fields = ("monto_descuento",)

    fieldsets = (
        ("Alumno y Clase", {"fields": ("alumno", "actividad", "clase_programada")}),
        ("Tipo de Pago", {"fields": ("tipo", "cantidad_clases", "metodo", "comprobante")}),
        ("Descuento Aplicado", {
            "fields": ("descuento", "monto_descuento"),
            "description": "El monto descontado se calcula automáticamente al guardar."
        }),
        ("Montos y Estado", {"fields": ("monto", "estado", "motivo_rechazo", "fecha_pago_real")}),
        ("Mercado Pago", {"fields": ("mercado_pago_id", "mercado_pago_status"), "classes": ("collapse",)}),
    )

    def has_module_permission(self, request):
        user = request.user
        if not user.is_authenticated:
            return False
        return user.is_superuser or getattr(user, 'rol_acceso_total', False) or getattr(user, 'rol_gestion_tesoreria', False) or getattr(user, 'es_profe', False)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user
        if not user.is_authenticated:
            return qs.none()
        if user.is_superuser or getattr(user, 'rol_acceso_total', False) or getattr(user, 'rol_gestion_tesoreria', False):
            return qs
        if getattr(user, 'es_profe', False):
            return qs.filter(alumno__sede__usuarios=user).distinct()
        return qs.none()

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        "id", "alumno", "clase_origen", "estado", "total", 
        "monto_costo_reposicion", "monto_comision", "monto_comision_asistente", "utilidad_neta_asociacion"
    )
    list_filter = ("estado", "profesor_venta", "clase_origen__sede")
    autocomplete_fields = ("alumno", "profesor_venta", "clase_origen")
    readonly_fields = ("monto_costo_reposicion", "monto_comision", "monto_comision_asistente", "utilidad_neta_asociacion")

    fieldsets = (
        ("Información General", {"fields": ("alumno", "clase_origen", "estado", "fecha_registro")}),
        ("Pagos y Comprobante", {"fields": ("metodo_pago", "total", "cuotas", "comprobante", "mercado_pago_id")}),
        ("AUDITORÍA DE UTILIDAD NETA", {
            "fields": (
                "monto_costo_reposicion",
                "profesor_venta", "porcentaje_comision", "monto_comision",
                "monto_comision_asistente",
                "utilidad_neta_asociacion"
            ),
        }),
    )

    def has_module_permission(self, request):
        user = request.user
        if not user.is_authenticated:
            return False
        es_delegado = Usuario.objects.filter(tesorero_autorizado=user, autorizacion_tesoreria_activa=True).exists()
        return (
            user.is_superuser or 
            getattr(user, 'rol_acceso_total', False) or 
            getattr(user, 'rol_gestion_tienda', False) or 
            getattr(user, 'rol_gestion_tesoreria', False) or 
            getattr(user, 'es_profe', False) or 
            es_delegado
        )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user
        if not user.is_authenticated:
            return qs.none()
        if user.is_superuser or getattr(user, 'rol_acceso_total', False) or getattr(user, 'rol_gestion_tesoreria', False) or getattr(user, 'rol_gestion_tienda', False):
            return qs
        query = Q(profesor_venta=user)
        profesores_que_delegaron = Usuario.objects.filter(tesorero_autorizado=user, autorizacion_tesoreria_activa=True)
        if profesores_que_delegaron.exists():
            query |= Q(profesor_venta__in=profesores_que_delegaron)
        if getattr(user, 'es_profe', False) or profesores_que_delegaron.exists():
            return qs.filter(query)
        return qs.none()

@admin.register(CategoriaProducto)
class CategoriaProductoAdmin(ModularAdminMixin, admin.ModelAdmin):
    rol_requerido = "rol_gestion_tienda"

class ProductoVarianteInline(admin.TabularInline):
    model = ProductoVariante
    extra = 1

@admin.register(Producto)
class ProductoAdmin(ModularAdminMixin, admin.ModelAdmin):
    rol_requerido = "rol_gestion_tienda"
    list_display = ("nombre", "precio", "costo_reposicion", "porcentaje_comision", "hay_stock_visual")
    list_editable = ("costo_reposicion", "porcentaje_comision")
    inlines = [ProductoVarianteInline]

    @admin.display(description="Stock?")
    def hay_stock_visual(self, obj):
        return "Disponibles" if obj.hay_stock else "Sin Stock"
