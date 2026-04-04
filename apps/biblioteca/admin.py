from django.contrib import admin
from .models import CategoriaContenido, MaterialEstudio, VisualizacionMaterial
from apps.usuarios.admin import ModularAdminMixin

class BibliotecaAdminMixin(ModularAdminMixin):
    rol_requerido = "rol_gestion_academia"

@admin.register(CategoriaContenido)
class CategoriaContenidoAdmin(BibliotecaAdminMixin, admin.ModelAdmin):
    list_display = ("nombre", "total_materiales")
    search_fields = ("nombre",)

    def total_materiales(self, obj):
        return obj.materiales.count()
    total_materiales.short_description = "Materiales"

@admin.register(MaterialEstudio)
class MaterialEstudioAdmin(BibliotecaAdminMixin, admin.ModelAdmin):
    list_display = ("titulo", "tipo", "categoria", "grado_minimo", "activo", "fecha_publicacion")
    list_filter = ("tipo", "categoria", "grado_minimo", "activo")
    search_fields = ("titulo", "descripcion")
    autocomplete_fields = ["categoria", "grado_minimo"]
    list_editable = ("activo", "grado_minimo")

@admin.register(VisualizacionMaterial)
class VisualizacionMaterialAdmin(BibliotecaAdminMixin, admin.ModelAdmin):
    list_display = ("alumno", "material", "fecha_hora")
    list_filter = ("fecha_hora", "material__categoria")
    search_fields = ("alumno__nombre", "alumno__apellido", "material__titulo")
    date_hierarchy = "fecha_hora"
