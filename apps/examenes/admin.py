from django.contrib import admin
from django.db import transaction
from .models import MesaExamen, InscripcionExamen
from apps.usuarios.admin import ModularAdminMixin

class ExamAdminMixin(ModularAdminMixin):
    rol_requerido = "rol_gestion_academia" # Masters/Managers can manage exams

class InscripcionExamenInline(admin.TabularInline):
    model = InscripcionExamen
    extra = 1
    autocomplete_fields = ('alumno', 'grado_actual', 'grado_a_aspirar')
    fields = ('alumno', 'grado_actual', 'grado_a_aspirar', 'resultado', 'procesado')
    readonly_fields = ('procesado',)

@admin.register(MesaExamen)
class MesaExamenAdmin(ExamAdminMixin, admin.ModelAdmin):
    list_display = ("id", "fecha", "lugar", "total_candidatos", "esta_abierta", "finalizada")
    list_filter = ("esta_abierta", "finalizada", "lugar")
    search_fields = ("lugar", "maestro_invitado")
    filter_horizontal = ("examinadores",)
    inlines = [InscripcionExamenInline]
    
    def total_candidatos(self, obj):
        return obj.candidatos.count()
    total_candidatos.short_description = "Nro. Alumnos"

@admin.register(InscripcionExamen)
class InscripcionExamenAdmin(ExamAdminMixin, admin.ModelAdmin):
    list_display = ("alumno", "mesa", "grado_a_aspirar", "resultado", "procesado")
    list_filter = ("resultado", "procesado", "grado_a_aspirar")
    list_select_related = ("alumno", "mesa", "grado_a_aspirar")
    search_fields = ("alumno__nombre", "alumno__apellido")
    autocomplete_fields = ("alumno", "mesa")
    actions = ["procesar_ascensos_masivo"]

    @admin.action(description="Ejecutar ascensos de grado (Aprobados)")
    def procesar_ascensos_masivo(self, request, queryset):
        count = 0
        try:
            with transaction.atomic():
                for insc in queryset.filter(resultado="aprobado", procesado=False):
                    insc.aplicar_ascenso()
                    insc.save() # Persiste el flag 'procesado' que aplicar_ascenso activó
                    count += 1
            self.message_user(request, f"Se procesaron {count} ascensos de grado exitosamente.")
        except Exception as e:
            self.message_user(request, f"Error en el proceso masivo: {str(e)}", level='error')
