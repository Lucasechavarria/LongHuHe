from django.db import models
from apps.usuarios.models import Usuario, Grado

class CategoriaContenido(models.Model):
    nombre = models.CharField(max_length=100)
    icono = models.CharField(max_length=50, default="book", help_text="Slug de icono Lucide/Heroicon")
    orden = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Biblioteca: Categoría"
        verbose_name_plural = "05.1 - Biblioteca: Categorías"
        ordering = ['orden']
        db_table = 'core_categoriacontenido'

    def __str__(self):
        return self.nombre

class MaterialEstudio(models.Model):
    class TipoMaterial(models.TextChoices):
        PDF = "pdf", "Documento PDF"
        VIDEO = "video", "URL de Video (YouTube/Vimeo)"
        TEORIA = "teoria", "Texto / Teoría"

    categoria = models.ForeignKey(CategoriaContenido, on_delete=models.CASCADE, related_name="materiales")
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    tipo = models.CharField(max_length=20, choices=TipoMaterial.choices, default=TipoMaterial.PDF)
    
    # El archivo fisico (opcional si es video)
    archivo = models.FileField(upload_to="biblioteca/", blank=True, null=True)
    video_url = models.URLField(blank=True, null=True, help_text="Pega el link de YouTube")
    contenido_teorico = models.TextField(blank=True, help_text="Para material de teoría directa (Texto/HTML)")

    # Acceso restringido (Task 6.1)
    grado_minimo = models.ForeignKey(Grado, on_delete=models.PROTECT, related_name="materiales_habilitados")
    
    fecha_publicacion = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True)
    descargable = models.BooleanField("Permitir Descarga", default=True)

    class Meta:
        verbose_name = "Biblioteca: Material"
        verbose_name_plural = "05.2 - Biblioteca: Materiales"
        ordering = ['grado_minimo__orden', 'titulo']

    def __str__(self):
        try:
            grado = self.grado_minimo.nombre if self.grado_minimo else "Cualquiera"
            return f"[{grado}] {self.titulo}"
        except Exception:
            return f"Material #{self.id}"

    @property
    def video_id(self):
        """ Extrae el ID de YouTube de un link de tipo: https://www.youtube.com/watch?v=dQw4w9WgXcQ """
        if not self.video_url:
            return None
        import re
        # Regex para extraer ID de youtube
        regex = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/(?:[^\/\n\s]+\/\S+\/|(?:v|e(?:mbed)?)\/|\S*?[?&]v=)|youtu\.be\/)([a-zA-Z0-9_-]{11})'
        match = re.search(regex, self.video_url)
        return match.group(1) if match else None

    def registrar_vista(self, alumno):
        """ Task 6.3: Registra o incrementa contador de vistas del material por un alumno """
        vista, created = VisualizacionMaterial.objects.get_or_create(
            alumno=alumno,
            material=self
        )
        if not created:
            vista.veces += 1
            vista.save()
        return vista

class VisualizacionMaterial(models.Model):
    """ Registro de tracking (Task 6.4) """
    alumno = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="vistas_biblioteca")
    material = models.ForeignKey(MaterialEstudio, on_delete=models.CASCADE, related_name="visualizaciones")
    fecha_hora = models.DateTimeField(auto_now_add=True)
    veces = models.PositiveIntegerField(default=1)

    class Meta:
        verbose_name = "Biblioteca: Registro de Vista"
        verbose_name_plural = "05.3 - Biblioteca: Tracking de Vistas"
        unique_together = ['alumno', 'material']

    def __str__(self):
        try:
            alumno_str = self.alumno.nombre_completo if self.alumno else "Alumno desconocido"
            material_str = self.material.titulo if self.material else "Material desconocido"
            return f"{alumno_str} vio {material_str} ({self.veces} veces)"
        except Exception:
            return f"Vista #{self.id}"

    @classmethod
    def registrar_vista(cls, alumno, material):
        vista, created = cls.objects.get_or_create(alumno=alumno, material=material)
        if not created:
            vista.veces += 1
            vista.save()
        return vista
