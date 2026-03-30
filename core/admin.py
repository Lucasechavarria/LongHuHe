from django import forms
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserChangeForm, UserCreationForm
from django.utils.html import format_html

from .models import Asistencia, Locacion, Pago, Usuario, Actividad


# =========================================================
# Formularios del admin para el usuario personalizado
# =========================================================

class UsuarioAdminCreationForm(UserCreationForm):
    """
    Formulario de alta en el admin para el modelo Usuario.
    """
    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = (
            "username",
            "nombre",
            "apellido",
            "celular",
            "dni",
            "locacion",
            "es_profe",
        )


class UsuarioAdminChangeForm(UserChangeForm):
    """
    Formulario de edición en el admin para el modelo Usuario.
    """
    class Meta(UserChangeForm.Meta):
        model = Usuario
        fields = "__all__"


# =========================================================
# Admin de Locacion
# =========================================================

@admin.register(Actividad)
class ActividadAdmin(admin.ModelAdmin):
    list_display = ("nombre", "precio_mes", "precio_clase")
    list_editable = ("precio_mes", "precio_clase")
    search_fields = ("nombre",)


@admin.register(Locacion)
class LocacionAdmin(admin.ModelAdmin):
    """
    Vista simple y clara para gestionar locaciones.
    """
    list_display = ("id", "nombre", "mapa_url", "total_usuarios")
    list_filter = ("nombre",)
    search_fields = ("nombre",)
    filter_horizontal = ("actividades",)
    ordering = ("nombre",)

    @admin.display(description="Usuarios")
    def total_usuarios(self, obj):
        return obj.usuarios.count()


# =========================================================
# Admin de Usuario
# =========================================================

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    """
    Admin del usuario personalizado.

    Se ha adaptado para:
    - mostrar datos útiles para el profesor
    - mantener compatibilidad con permisos/grupos/staff
    """
    form = UsuarioAdminChangeForm
    add_form = UsuarioAdminCreationForm

    list_display = (
        "id",
        "nombre",
        "apellido",
        "celular",
        "locacion",
        "es_profe",
        "is_staff",
        "is_active",
    )
    list_filter = (
        "es_profe",
        "locacion",
        "actividades",
        "is_staff",
        "is_superuser",
        "is_active",
    )
    search_fields = (
        "nombre",
        "apellido",
        "celular",
        "dni",
        "username",
    )
    ordering = ("apellido", "nombre")

    fieldsets = (
        ("Acceso", {
            "fields": ("username", "password")
        }),
        ("Información Marcial", {
            "fields": ("nombre", "apellido", "celular", "locacion", "actividades", "es_profe")
        }),
        ("Datos Personales (SeniorUX)", {
            "fields": ("dni", "fecha_nacimiento", "domicilio", "localidad")
        }),
        ("Permisos", {
            "fields": (
                "is_active",
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            )
        }),
        ("Fechas importantes", {
            "fields": ("last_login", "date_joined")
        }),
    )

    add_fieldsets = (
        ("Alta rápida de usuario", {
            "classes": ("wide",),
            "fields": (
                "username",
                "nombre",
                "apellido",
                "celular",
                "dni",
                "locacion",
                "actividades",
                "es_profe",
                "password1",
                "password2",
                "is_staff",
                "is_superuser",
            ),
        }),
    )


# =========================================================
# Admin de Asistencia
# =========================================================

@admin.register(Asistencia)
class AsistenciaAdmin(admin.ModelAdmin):
    """
    Vista tipo planilla para revisar asistencia rápidamente.
    """
    list_display = (
        "id",
        "alumno",
        "actividad",
        "celular_alumno",
        "locacion_alumno",
        "fecha_hora",
    )
    list_filter = (
        "fecha_hora",
        "actividad",
        "alumno__locacion",
    )
    search_fields = (
        "alumno__nombre",
        "alumno__apellido",
        "alumno__celular",
    )
    autocomplete_fields = ("alumno",)
    date_hierarchy = "fecha_hora"
    ordering = ("-fecha_hora",)

    @admin.display(description="Celular")
    def celular_alumno(self, obj):
        return obj.alumno.celular

    @admin.display(description="Locación")
    def locacion_alumno(self, obj):
        return obj.alumno.locacion


# =========================================================
# Admin de Pago
# =========================================================

@admin.register(Pago)
class PagoAdmin(admin.ModelAdmin):
    """
    Admin optimizado para revisión rápida de pagos.

    Claves UX para el profesor:
    - filtro inmediato por estado pendiente
    - edición del estado directamente en listado
    - búsqueda por nombre, apellido o celular
    - acceso rápido al comprobante
    """
    list_display = (
        "id",
        "alumno",
        "actividad",
        "locacion_alumno",
        "tipo",
        "cantidad_clases",
        "metodo",
        "estado",
        "ver_comprobante",
        "fecha_registro",
    )
    list_filter = (
        "estado",
        "actividad",
        "tipo",
        "metodo",
        "fecha_registro",
        "alumno__locacion",
    )
    search_fields = (
        "alumno__nombre",
        "alumno__apellido",
        "alumno__celular",
    )
    autocomplete_fields = ("alumno",)
    date_hierarchy = "fecha_registro"
    ordering = ("-fecha_registro",)

    # Permite cambiar el estado directamente desde la lista.
    # Importante: el primer campo mostrado NO puede ser editable.
    list_editable = ("estado",)

    actions = ("marcar_como_aprobado", "marcar_como_pendiente")

    @admin.display(description="Locación")
    def locacion_alumno(self, obj):
        return obj.alumno.locacion

    @admin.display(description="Comprobante")
    def ver_comprobante(self, obj):
        if obj.comprobante:
            return format_html(
                '<a href="{}" target="_blank" style="font-weight:600;">Ver archivo</a>',
                obj.comprobante.url
            )
        return "-"

    @admin.action(description="Marcar pagos seleccionados como APROBADOS")
    def marcar_como_aprobado(self, request, queryset):
        actualizados = queryset.update(estado=Pago.EstadoPago.APROBADO)
        self.message_user(request, f"{actualizados} pago(s) marcados como aprobados.")

    @admin.action(description="Marcar pagos seleccionados como PENDIENTES")
    def marcar_como_pendiente(self, request, queryset):
        actualizados = queryset.update(estado=Pago.EstadoPago.PENDIENTE)
        self.message_user(request, f"{actualizados} pago(s) marcados como pendientes.")
