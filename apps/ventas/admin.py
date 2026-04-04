from django.contrib import admin
from django.db.models import Q
from apps.usuarios.models import Usuario
from apps.usuarios.admin import ModularAdminMixin
from .models import Pago, Pedido, CategoriaProducto, Producto, ProductoVariante, PedidoItem

@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("id", "alumno", "tipo", "metodo", "estado", "fecha_registro")
    list_filter = ("estado", "tipo", "fecha_registro")
    search_fields = ("alumno__nombre", "alumno__apellido")
    autocomplete_fields = ("alumno",)
    list_editable = ("estado",)

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
