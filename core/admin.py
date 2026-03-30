from django import forms
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
# Admin de Marketplace (Horarios y Clases)
# =========================================================

@admin.register(Horario)
class HorarioAdmin(admin.ModelAdmin):
    list_display = ("dia", "hora_inicio", "hora_fin")
    list_filter = ("dia",)
    ordering = ("dia", "hora_inicio")


@admin.register(ClaseProgramada)
class ClaseProgramadaAdmin(admin.ModelAdmin):
    list_display = ("actividad", "locacion", "profesor")
    list_filter = ("actividad", "locacion", "profesor")
    search_fields = ("profesor__nombre", "profesor__apellido", "actividad__nombre", "locacion__nombre")
    filter_horizontal = ("horarios",)
    autocomplete_fields = ("profesor",)


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
            "fields": ("nombre", "apellido", "celular", "locacion", "actividades", "es_profe", "fecha_ingreso_real")
        }),
        ("Salud y Seguridad", {
            "fields": ("alergias", "condiciones_medicas", "contacto_emergencia_nombre", "contacto_emergencia_telefono", "apto_medico")
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
# Admin de Examen / Evolución
# =========================================================

@admin.register(Examen)
class ExamenAdmin(admin.ModelAdmin):
    list_display = ("alumno", "grado", "fecha", "examinador")
    list_filter = ("grado", "fecha", "examinador")
    search_fields = ("alumno__nombre", "alumno__apellido", "grado")
    autocomplete_fields = ("alumno", "examinador")
    
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
        "clase_programada",
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
        "tipo",
        "metodo",
        "fecha_registro",
        "clase_programada",
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


# =========================================================
# Admin de Tienda E-Commerce
# =========================================================

@admin.register(CategoriaProducto)
class CategoriaProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "categoria", "precio", "stock", "activo", "permite_backorder")
    list_filter = ("categoria", "activo", "permite_backorder")
    search_fields = ("nombre", "descripcion")
    list_editable = ("precio", "stock", "activo", "permite_backorder")


class PedidoItemInline(admin.TabularInline):
    model = PedidoItem
    extra = 1

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    """
    Vista del administrador central para la Tienda.
    Muestra rápidamente qué facturar y con qué profesor liquidar comisiones.
    """
    list_display = ("id", "alumno", "fecha_registro", "estado", "total", "metodo_pago", "backorder", "monto_comision")
    list_filter = ("estado", "metodo_pago", "backorder", "fecha_registro", "profesor_venta")
    search_fields = ("alumno__nombre", "alumno__apellido", "id")
    list_editable = ("estado",)
    inlines = [PedidoItemInline]
    autocomplete_fields = ("alumno", "profesor_venta")
    
    actions = ("marcar_como_pagado", "marcar_como_entregado")

    @admin.action(description="Marcar pedidos como PAGADOS")
    def marcar_como_pagado(self, request, queryset):
        queryset.update(estado=Pedido.Estado.PAGADO)
        
    @admin.action(description="Marcar pedidos como ENTREGADOS")
    def marcar_como_entregado(self, request, queryset):
        queryset.update(estado=Pedido.Estado.ENTREGADO)


# =========================================================
# Admin de Academia Digital (Biblioteca)
# =========================================================

@admin.register(CategoriaContenido)
class CategoriaContenidoAdmin(admin.ModelAdmin):
    list_display = ("nombre",)
    search_fields = ("nombre",)

@admin.register(Documento)
class DocumentoAdmin(admin.ModelAdmin):
    list_display = ("titulo", "categoria", "nivel_acceso", "descargable", "fecha_subida")
    list_filter = ("categoria", "nivel_acceso", "descargable")
    search_fields = ("titulo", "descripcion")

@admin.register(VideoTutorial)
class VideoTutorialAdmin(admin.ModelAdmin):
    list_display = ("titulo", "categoria", "nivel_acceso", "youtube_id", "fecha_subida")
    list_filter = ("categoria", "nivel_acceso")
    search_fields = ("titulo", "descripcion", "youtube_id")
