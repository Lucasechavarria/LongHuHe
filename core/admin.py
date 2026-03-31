from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.html import format_html

from .models import (
    Asistencia, Locacion, Pago, Usuario, Actividad, Horario, ClaseProgramada, 
    Examen, CategoriaProducto, Producto, Pedido, PedidoItem,
    CategoriaContenido, Documento, VideoTutorial
)

# =========================================================
# 1. GESTIÓN DE USUARIOS (LOGÍSTICA Y CARNETS)
# =========================================================

class UsuarioAdminCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ("username", "nombre", "apellido", "celular", "dni", "locacion", "es_profe")

class UsuarioAdminChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = Usuario
        fields = "__all__"

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    form = UsuarioAdminChangeForm
    add_form = UsuarioAdminCreationForm

    list_display = ("id", "nombre", "apellido", "celular", "locacion", "es_profe", "estado_pago_visual", "is_active")
    list_filter = ("es_profe", "locacion", "actividades", "is_active")
    search_fields = ("nombre", "apellido", "celular", "dni", "username")
    ordering = ("apellido", "nombre")

    fieldsets = (
        ("Acceso", {"fields": ("username", "password")}),
        ("Carnet y ERP", {"fields": ("uuid_carnet", "fecha_vencimiento_cuota")}),
        ("Información Marcial", {"fields": ("nombre", "apellido", "celular", "locacion", "actividades", "es_profe", "fecha_ingreso_real")}),
        ("Salud y Seguridad (Alertas Críticas)", {"fields": ("alergias", "condiciones_medicas", "contacto_emergencia_nombre", "contacto_emergencia_telefono", "apto_medico")}),
        ("Datos Personales", {"fields": ("dni", "fecha_nacimiento", "domicilio", "localidad")}),
        ("Permisos", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
    )
    readonly_fields = ("uuid_carnet",)

    @admin.display(description="Estado Pago")
    def estado_pago_visual(self, obj):
        color = obj.color_estado
        return format_html('<b style="color:{}; text-transform:uppercase;">{}</b>', color, obj.estado_morosidad)

# =========================================================
# 2. GESTIÓN ACADÉMICA Y SEDES (EL NÚCLEO)
# =========================================================

@admin.register(Actividad)
class ActividadAdmin(admin.ModelAdmin):
    list_display = ("nombre", "precio_mes", "precio_clase")
    list_editable = ("precio_mes", "precio_clase")
    search_fields = ("nombre",)

@admin.register(Horario)
class HorarioAdmin(admin.ModelAdmin):
    list_display = ("dia", "hora_inicio", "hora_fin")
    list_filter = ("dia",)
    ordering = ("dia", "hora_inicio")

class ClaseProgramadaInline(admin.StackedInline):
    """La Magia de Sedes: Configura todo lo que pasa en la sede desde aquí."""
    model = ClaseProgramada
    extra = 1
    autocomplete_fields = ("profesor",)
    filter_horizontal = ("horarios",)
    classes = ('collapse',) # Opcional: para que no ocupe tanto espacio si hay muchas

@admin.register(Locacion)
class LocacionAdmin(admin.ModelAdmin):
    list_display = ("nombre", "mapa_url", "total_usuarios")
    search_fields = ("nombre",)
    filter_horizontal = ("actividades",)
    inlines = [ClaseProgramadaInline]
    ordering = ("nombre",)

    @admin.display(description="Usuarios")
    def total_usuarios(self, obj):
        return obj.usuarios.count()

@admin.register(ClaseProgramada)
class ClaseProgramadaAdmin(admin.ModelAdmin):
    list_display = ("actividad", "locacion", "profesor")
    list_filter = ("actividad", "locacion", "profesor")
    autocomplete_fields = ("profesor",)
    filter_horizontal = ("horarios",)

@admin.register(Examen)
class ExamenAdmin(admin.ModelAdmin):
    list_display = ("alumno", "grado", "fecha", "examinador")
    list_filter = ("grado", "fecha")
    search_fields = ("alumno__nombre", "alumno__apellido", "grado")
    autocomplete_fields = ("alumno", "examinador")

# =========================================================
# 3. CONTROL DE ASISTENCIA Y FINANZAS
# =========================================================

@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    list_display = ("alumno", "actividad", "celular_alumno", "locacion_alumno", "fecha_hora")
    list_filter = ("fecha_hora", "actividad", "alumno__locacion")
    search_fields = ("alumno__nombre", "alumno__apellido", "alumno__celular")
    autocomplete_fields = ("alumno",)
    date_hierarchy = "fecha_hora"

    @admin.display(description="Celular")
    def celular_alumno(self, obj): return obj.alumno.celular

    @admin.display(description="Locación")
    def locacion_alumno(self, obj): return obj.alumno.locacion

@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    list_display = ("id", "alumno", "tipo", "metodo", "estado", "ver_comprobante", "fecha_registro")
    list_filter = ("estado", "tipo", "metodo", "fecha_registro")
    search_fields = ("alumno__nombre", "alumno__apellido")
    autocomplete_fields = ("alumno",)
    list_editable = ("estado",)
    date_hierarchy = "fecha_registro"
    actions = ("marcar_como_aprobado", "marcar_como_pendiente")

    @admin.display(description="Comprobante")
    def ver_comprobante(self, obj):
        if obj.comprobante:
            return format_html('<a href="{}" target="_blank" style="font-weight:bold; color:#f97316;">Ver Archivo</a>', obj.comprobante.url)
        return "-"

    @admin.action(description="Aprobar pagos seleccionados")
    def marcar_como_aprobado(self, request, queryset):
        queryset.update(estado=Pago.EstadoPago.APROBADO)

    @admin.action(description="Pasar a pendiente")
    def marcar_como_pendiente(self, request, queryset):
        queryset.update(estado=Pago.EstadoPago.PENDIENTE)

# =========================================================
# 4. TIENDA INTERNA (E-COMMERCE)
# =========================================================

@admin.register(CategoriaProducto)
class CategoriaProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre",)

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "precio", "stock", "cuotas_maximas", "porcentaje_comision", "activo")
    list_filter = ("categoria", "activo")
    search_fields = ("nombre",)
    list_editable = ("precio", "stock", "cuotas_maximas", "porcentaje_comision", "activo")

class PedidoItemInline(admin.TabularInline):
    model = PedidoItem
    extra = 1

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "alumno", "fecha_registro", "estado", "total", "metodo_pago", "profesor_venta", "monto_comision")
    list_filter = ("estado", "metodo_pago", "profesor_venta")
    search_fields = ("alumno__nombre", "alumno__apellido")
    list_editable = ("estado",)
    inlines = [PedidoItemInline]
    autocomplete_fields = ("alumno", "profesor_venta")

# =========================================================
# 5. BIBLIOTECA DIGITAL
# =========================================================

@admin.register(CategoriaContenido)
class CategoriaContenidoAdmin(admin.ModelAdmin):
    list_display = ("nombre",)

@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "categoria", "nivel_acceso", "descargable")
    list_filter = ("categoria", "nivel_acceso")
    search_fields = ("titulo",)

@admin.register(VideoTutorial)
class VideoTutorialAdmin(admin.ModelAdmin):
    list_display = ("titulo", "categoria", "nivel_acceso")
    list_filter = ("categoria", "nivel_acceso")
    search_fields = ("titulo",)
