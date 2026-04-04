from django.contrib import admin
from apps.usuarios.admin import ModularAdminMixin
from .models import RegistroAsistencia

class AlumnosAdminMixin(ModularAdminMixin):
    rol_requerido = "rol_gestion_alumnos"

@admin.register(RegistroAsistencia)
class RegistroAsistenciaAdmin(AlumnosAdminMixin, admin.ModelAdmin):
    list_display = ("alumno", "actividad", "fecha_hora")
    list_filter = ("fecha_hora", "actividad", "alumno__sede")
    search_fields = ("alumno__nombre", "alumno__apellido")
    autocomplete_fields = ("alumno",)
    date_hierarchy = "fecha_hora"
