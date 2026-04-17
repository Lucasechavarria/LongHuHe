from django.contrib import admin
from apps.usuarios.admin import ModularAdminMixin
from .models import Actividad, Sede, Cronograma, InscripcionClase

class SedesAdminMixin(ModularAdminMixin):
    rol_requerido = "rol_gestion_sedes"

class InscripcionInline(admin.TabularInline):
    model = InscripcionClase
    extra = 0
    autocomplete_fields = ("alumno",)

@admin.register(Actividad)
class ActividadAdmin(SedesAdminMixin, admin.ModelAdmin):
    list_display = ("nombre", "precio_mes", "precio_clase")
    list_editable = ("precio_mes", "precio_clase")
    search_fields = ("nombre",)

@admin.register(Sede)
class SedeAdmin(SedesAdminMixin, admin.ModelAdmin):
    list_display = ("nombre", "total_usuarios")
    search_fields = ("nombre",)

    @admin.display(description="Usuarios Registrados")
    def total_usuarios(self, obj):
        try:
            return obj.usuarios.count()
        except Exception:
            return 0

@admin.register(Cronograma)
class CronogramaAdmin(SedesAdminMixin, admin.ModelAdmin):
    list_display = ("actividad", "sede", "dia", "hora_inicio", "cupo", "total_inscriptos", "profesor")
    list_filter = ("actividad", "sede", "profesor", "dia")
    list_select_related = ("actividad", "sede", "profesor")
    autocomplete_fields = ("profesor", "profesor_asistente")
    list_editable = ("dia", "hora_inicio", "cupo", "profesor")
    search_fields = ("actividad__nombre", "sede__nombre", "profesor__nombre", "profesor__apellido")
    inlines = [InscripcionInline]

    @admin.display(description="Inscriptos")
    def total_inscriptos(self, obj):
        try:
            count = obj.alumnos_inscritos.filter(estado='regular').count()
            return f"{count} / {obj.cupo if obj.cupo is not None else '?'}"
        except Exception:
            return "Error"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        user = request.user
        if not user.is_authenticated:
            return qs.none()
        if user.is_superuser or getattr(user, 'rol_acceso_total', False) or getattr(user, 'rol_gestion_sedes', False):
            return qs
        return qs.filter(profesor=user)

@admin.register(InscripcionClase)
class InscripcionClaseAdmin(SedesAdminMixin, admin.ModelAdmin):
    list_display = ("alumno", "clase", "estado", "fecha_inscripcion")
    list_filter = ("estado", "clase__sede", "clase__actividad")
    search_fields = ("alumno__nombre", "alumno__apellido", "alumno__dni")
    autocomplete_fields = ("alumno", "clase")
