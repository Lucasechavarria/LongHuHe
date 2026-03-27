from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class Locacion(models.Model):
    """
    Lugar físico donde el maestro da clase.
    Ejemplos: 'Centro de Jubilados San Martín', 'Plaza Norte', etc.
    """
    nombre = models.CharField(max_length=120)
    actividades = models.ManyToManyField("Actividad", related_name="locaciones", blank=True)
    mapa_url = models.URLField("Enlace Google Maps", max_length=500, blank=True, null=True)

    class Meta:
        verbose_name = "Locación"
        verbose_name_plural = "Locaciones"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Actividad(models.Model):
    """
    Actividades ofrecidas por la escuela (Tai-Chi, Kung-Fu, Defensa Personal, etc.)
    """
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    precio_mes = models.DecimalField("Precio Mensual", max_digits=10, decimal_places=2, default=0)
    precio_clase = models.DecimalField("Precio Clase Suelta", max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = "Actividad"
        verbose_name_plural = "Actividades"

    def __str__(self):
        return self.nombre


class Usuario(AbstractUser):
    """
    Usuario principal del sistema.

    Extiende AbstractUser para mantener compatibilidad completa con Django Admin,
    permisos, grupos, etc.

    Nota importante:
    - Conservamos los campos heredados de autenticación (username, password, etc.)
      porque Django Admin los necesita bien resueltos.
    - Para el negocio del MVP, los campos clave son: nombre, apellido, celular,
      locacion y es_profe.
    """

    # Opcionalmente ocultamos first_name y last_name heredados para evitar duplicidad
    # conceptual con nombre y apellido.
    first_name = None
    last_name = None

    nombre = models.CharField(max_length=120)
    apellido = models.CharField(max_length=120)
    celular = models.CharField(max_length=30, unique=True)
    locacion = models.ForeignKey(
        Locacion,
        on_delete=models.PROTECT,
        related_name="usuarios",
        null=True,
    )
    es_profe = models.BooleanField(default=False)

    # Nuevos campos para adultos mayores
    dni = models.CharField("DNI", max_length=15, blank=True)
    fecha_nacimiento = models.DateField("Fecha de Nacimiento", null=True, blank=True)
    domicilio = models.CharField("Domicilio", max_length=255, blank=True)
    localidad = models.CharField("Localidad", max_length=150, blank=True)

    actividades = models.ManyToManyField(Actividad, blank=True, related_name="alumnos")

    class Meta:
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"
        ordering = ["apellido", "nombre"]

    def save(self, *args, **kwargs):
        if not self.username and self.celular:
            # Limpiamos el celular de espacios, guiones y puntos para un username válido
            clean_username = self.celular.replace(" ", "").replace("-", "").replace(".", "")
            self.username = clean_username[:150]
        super().save(*args, **kwargs)

    def __str__(self):
        rol = "Profesor" if self.es_profe else "Alumno"
        return f"{self.apellido}, {self.nombre} ({rol}) - {self.celular}"

    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}".strip()


class Asistencia(models.Model):
    """
    Registro simple de presencia del alumno.
    Se crea cuando pulsa el botón 'Estoy aquí'.
    """
    alumno = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name="asistencias",
    )
    actividad = models.ForeignKey(
        Actividad, 
        on_delete=models.CASCADE, 
        related_name="asistencias",
        null=True
    )
    fecha_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Asistencia"
        verbose_name_plural = "Asistencias"
        ordering = ["-fecha_hora"]

    def __str__(self):
        fecha = self.fecha_hora.strftime("%d/%m/%Y %H:%M")
        return f"Asistencia de {self.alumno.nombre_completo} - {fecha}"


class Pago(models.Model):
    """
    Aviso de pago generado por el alumno.

    Reglas funcionales:
    - Si el tipo es 'paquete', se espera cantidad_clases.
    - Si el método es 'transferencia', se espera comprobante.
    - Si el método es 'efectivo', no hace falta comprobante.
    """

    class TipoPago(models.TextChoices):
        MES = "mes", "Mes Completo"
        CLASE_SUELTA = "clase_suelta", "1 Clase"
        PAQUETE = "paquete", "Paquete de Clases"

    class MetodoPago(models.TextChoices):
        TRANSFERENCIA = "transferencia", "Transferencia Bancaria"
        MERCADOPAGO = "mercadopago", "Mercado Pago"
        EFECTIVO = "efectivo", "En Efectivo"

    class EstadoPago(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente"
        APROBADO = "aprobado", "Aprobado"

    alumno = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name="pagos",
    )
    actividad = models.ForeignKey(
        Actividad,
        on_delete=models.CASCADE,
        related_name="pagos",
        null=True
    )
    tipo = models.CharField(max_length=20, choices=TipoPago.choices)
    cantidad_clases = models.IntegerField(null=True, blank=True)
    metodo = models.CharField(max_length=20, choices=MetodoPago.choices)
    comprobante = models.FileField(
        upload_to="comprobantes/",
        null=True,
        blank=True,
    )
    estado = models.CharField(
        max_length=20,
        choices=EstadoPago.choices,
        default=EstadoPago.PENDIENTE,
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ["-fecha_registro"]

    def __str__(self):
        fecha = self.fecha_registro.strftime("%d/%m/%Y %H:%M")
        return (
            f"Pago de {self.alumno.nombre_completo} - "
            f"{self.get_tipo_display()} - "
            f"{self.get_estado_display()} - {fecha}"
        )

    def clean(self):
        """
        Validaciones de negocio para mantener coherencia en el modelo.
        """
        errores = {}

        # Si es paquete, la cantidad de clases debe existir y ser mayor que 0.
        if self.tipo == self.TipoPago.PAQUETE:
            if not self.cantidad_clases or self.cantidad_clases <= 0:
                errores["cantidad_clases"] = "Debes indicar cuántas clases incluye el paquete."
        else:
            # Para 'mes' o 'clase_suelta', este campo no tiene sentido.
            self.cantidad_clases = None

        # Si pagó por transferencia, debe adjuntar comprobante.
        if self.metodo == self.MetodoPago.TRANSFERENCIA and not self.comprobante:
            errores["comprobante"] = "Debes adjuntar el comprobante para pagos por transferencia."

        if errores:
            raise ValidationError(errores)
