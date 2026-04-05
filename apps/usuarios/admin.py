from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm
from django.utils.html import format_html
from .models import Usuario, Grado, Examen

class ModularAdminMixin:
    """Mixin para restringir acceso segun los roles bolleanos del Usuario."""
    rol_requerido = None

    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        if getattr(request.user, 'rol_acceso_total', False) or request.user.is_superuser:
            return True
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

class ExamenInline(admin.TabularInline):
    model = Examen
    fk_name = "alumno"
    extra = 1
    autocomplete_fields = ("examinador", "grado")
    fields = ("grado", "fecha", "examinador", "examinador_externo", "observaciones")

class UsuarioAdminCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ("nombre", "apellido", "celular", "dni", "sede", "es_profe")

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    add_form = UsuarioAdminCreationForm
    list_display = ("id", "nombre", "apellido", "celular", "sede", "es_profe", "estado_pago_visual", "is_active")
    list_filter = ("es_profe", "rol_acceso_total", "sede", "is_active")
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
        ("Información Marcial", {"fields": ("nombre", "apellido", "celular", "sede", "grado", "actividades", "fecha_ingreso_real")}),
        ("Salud y Seguridad (Alertas Críticas)", {"fields": ("alergias", "condiciones_medicas", "contacto_emergencia_nombre", "contacto_emergencia_telefono", "apto_medico")}),
        ("Datos Personales", {"fields": ("dni", "fecha_nacimiento", "domicilio", "localidad")}),
        ("Permisos Django (Avanzado)", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"), "classes": ("collapse",)}),
    )
    readonly_fields = ("uuid_carnet",)
    inlines = [ExamenInline]

    @admin.display(description="Estado Pago")
    def estado_pago_visual(self, obj):
        color = obj.color_estado
        return format_html('<b style="color:{}; text-transform:uppercase;">{}</b>', color, obj.estado_morosidad)

    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or getattr(request.user, 'rol_gestion_alumnos', False) or getattr(request.user, 'rol_acceso_total', False)

@admin.register(Grado)
class GradoAdmin(admin.ModelAdmin):
    list_display = ("id", "orden", "nombre", "nivel_desbloqueado")
    list_editable = ("orden", "nombre", "nivel_desbloqueado")
    search_fields = ("nombre",)

    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser or getattr(request.user, 'rol_gestion_alumnos', False) or getattr(request.user, 'rol_acceso_total', False)
