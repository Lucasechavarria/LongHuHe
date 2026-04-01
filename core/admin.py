from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.html import format_html
from django.db.models import Q

from .models import (
    Asistencia, Locacion, Pago, Usuario, Actividad, Horario, ClaseProgramada, 
    Grado, Examen, CategoriaProducto, Producto, ProductoVariante, Pedido, PedidoItem,
    CategoriaContenido, Documento, VideoTutorial
)

# =========================================================
# MIXINS DE SEGURIDAD MODULAR (Punto 5 del ERP)
# =========================================================

class ModularAdminMixin:
    """Mixin para restringir acceso segun los roles bolleanos del Usuario."""
    rol_requerido = None

    def has_module_permission(self, request):
        if not request.user.is_authenticated: return False
        if request.user.rol_acceso_total or request.user.is_superuser: return True
        if self.rol_requerido and getattr(request.user, self.rol_requerido, False):
            return True
        return False

    def has_view_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_change_permission(self, request, obj=None):
        return self.has_module_permission(request)

    def has_add_permission(self, request):
        return self.has_module_permission(request)

    def has_delete_permission(self, request, obj=None):
        return self.has_module_permission(request)


# =========================================================
# 1. GESTIÓN DE USUARIOS (SEGURIDAD Y ROLES)
# =========================================================

class UsuarioAdminCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ("username", "nombre", "apellido", "celular", "dni", "locacion", "es_profe")

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("id", "nombre", "apellido", "celular", "locacion", "es_profe", "estado_pago_visual", "is_active")
    list_filter = ("es_profe", "rol_acceso_total", "locacion", "is_active")
    search_fields = ("nombre", "apellido", "celular", "dni", "username")
    ordering = ("apellido", "nombre")

    fieldsets = (
        ("Acceso", {"fields": ("username", "password")}),
        ("SEGURIDAD Y ROLES ERP", {
            "fields": (
                "rol_acceso_total",
                "rol_gestion_alumnos", 
                "rol_gestion_sedes", 
                "rol_gestion_tienda", 
                "rol_gestion_tesoreria", 
                "rol_gestion_academia",
                "es_profe"
            ),
            "description": "El Acceso Total otorga permisos de Superusuario. Los demás roles son granulares."
        }),
        ("DELEGACIÓN FINANCIERA", {
            "fields": ("tesorero_autorizado", "autorizacion_tesoreria_activa"),
            "description": "Permite que otro usuario gestione la tesorería de un profesor."
        }),
        ("Carnet y ERP", {"fields": ("uuid_carnet", "fecha_vencimiento_cuota")}),
        ("Información Marcial", {"fields": ("nombre", "apellido", "celular", "locacion", "actividades", "fecha_ingreso_real")}),
        ("Salud y Seguridad (Alertas Críticas)", {"fields": ("alergias", "condiciones_medicas", "contacto_emergencia_nombre", "contacto_emergencia_telefono", "apto_medico")}),
        ("Datos Personales", {"fields": ("dni", "fecha_nacimiento", "domicilio", "localidad")}),
        ("Permisos Django (Avanzado)", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"), "classes": ("collapse",)}),
    )
    readonly_fields = ("uuid_carnet",)

    @admin.display(description="Estado Pago")
    def estado_pago_visual(self, obj):
        color = obj.color_estado
        return format_html('<b style="color:{}; text-transform:uppercase;">{}</b>', color, obj.estado_morosidad)

    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or getattr(request.user, 'rol_gestion_alumnos', False) or getattr(request.user, 'rol_acceso_total', False)


# =========================================================
# 2. GESTIÓN DE SEDES Y CLASES (Con Asistentes)
# =========================================================

class SedesAdminMixin(ModularAdminMixin):
    rol_requerido = "rol_gestion_sedes"

@admin.register(Actividad)
class ActividadAdmin(SedesAdminMixin, admin.ModelAdmin):
    list_display = ("nombre", "precio_mes", "precio_clase")
    list_editable = ("precio_mes", "precio_clase")
    search_fields = ("nombre",)

@admin.register(Horario)
class HorarioAdmin(SedesAdminMixin, admin.ModelAdmin):
    list_display = ("dia", "hora_inicio", "hora_fin")
    list_filter = ("dia",)
    ordering = ("dia", "hora_inicio")

class ClaseProgramadaInline(admin.StackedInline):
    model = ClaseProgramada
    extra = 1
    autocomplete_fields = ("profesor", "profesor_asistente")
    filter_horizontal = ("horarios",)
    classes = ('collapse',)

@admin.register(Locacion)
class LocacionAdmin(SedesAdminMixin, admin.ModelAdmin):
    list_display = ("nombre", "total_usuarios")
    search_fields = ("nombre",)
    filter_horizontal = ("actividades",)
    inlines = [ClaseProgramadaInline]

    @admin.display(description="Usuarios")
    def total_usuarios(self, obj): return obj.usuarios.count()

@admin.register(ClaseProgramada)
class ClaseProgramadaAdmin(SedesAdminMixin, admin.ModelAdmin):
    list_display = ("actividad", "locacion", "profesor", "profesor_asistente", "porcentaje_comision_asistente")
    list_filter = ("actividad", "locacion", "profesor")
    autocomplete_fields = ("profesor", "profesor_asistente")
    filter_horizontal = ("horarios",)
    list_editable = ("profesor_asistente", "porcentaje_comision_asistente")
    search_fields = ("actividad__nombre", "locacion__nombre", "profesor__nombre", "profesor__apellido")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user
        if not user.is_authenticated:
            return qs.none()
        if user.is_superuser or getattr(user, 'rol_acceso_total', False) or getattr(user, 'rol_gestion_sedes', False):
            return qs
        # Si es profesor titular de la sede, puede ver sus clases para asignar asistentes
        return qs.filter(profesor=user)


# =========================================================
# 3. ALUMNOS, ASISTENCIA Y EXÁMENES
# =========================================================

class AlumnosAdminMixin(ModularAdminMixin):
    rol_requerido = "rol_gestion_alumnos"

@admin.register(Asistencia)
class AsistenciaAdmin(AlumnosAdminMixin, admin.ModelAdmin):
    list_display = ("alumno", "actividad", "fecha_hora")
    list_filter = ("fecha_hora", "actividad", "alumno__locacion")
    search_fields = ("alumno__nombre", "alumno__apellido")
    autocomplete_fields = ("alumno",)
    date_hierarchy = "fecha_hora"

@admin.register(Grado)
class GradoAdmin(AlumnosAdminMixin, admin.ModelAdmin):
    list_display = ("id", "orden", "nombre", "nivel_desbloqueado")
    list_editable = ("orden", "nombre", "nivel_desbloqueado")
    search_fields = ("nombre",)

@admin.register(Examen)
class ExamenAdmin(AlumnosAdminMixin, admin.ModelAdmin):
    list_display = ("alumno", "grado", "fecha", "examinador")
    list_filter = ("grado", "fecha")
    autocomplete_fields = ("alumno", "examinador", "grado")


# =========================================================
# 4. TESORERÍA Y FINANZAS (Capa de Privacidad)
# =========================================================

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
            return qs.filter(alumno__locacion__usuarios=user).distinct()
        return qs.none()


# =========================================================
# 5. TIENDA Y AUDITORÍA DE UTILIDAD NETA (ERP Premium)
# =========================================================

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = (
        "id", "alumno", "clase_origen", "estado", "total", 
        "monto_costo_reposicion", "monto_comision", "monto_comision_asistente", "utilidad_neta_asociacion"
    )
    list_filter = ("estado", "profesor_venta", "clase_origen__locacion")
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
            "description": "Desglose automático de costos de stock y comisiones de profesores/asistentes."
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


# =========================================================
# 6. ACADEMIA DIGITAL
# =========================================================

class AcademiaAdminMixin(ModularAdminMixin):
    rol_requerido = "rol_gestion_academia"

@admin.register(CategoriaContenido)
class CategoriaContenidoAdmin(AcademiaAdminMixin, admin.ModelAdmin): pass

@admin.register(Documento)
class DocumentoAdmin(AcademiaAdminMixin, admin.ModelAdmin):
    list_display = ("titulo", "categoria", "nivel_acceso")

@admin.register(VideoTutorial)
class VideoTutorialAdmin(AcademiaAdminMixin, admin.ModelAdmin):
    list_display = ("titulo", "categoria", "nivel_acceso")
