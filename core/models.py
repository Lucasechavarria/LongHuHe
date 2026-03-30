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

    # Campos de Mercado Pago para Profesores (Marketplace)
    mp_access_token = models.CharField("MP Access Token", max_length=255, blank=True, null=True)
    mp_public_key = models.CharField("MP Public Key", max_length=255, blank=True, null=True)

    # Nuevos campos para adultos mayores
    dni = models.CharField("DNI", max_length=15, blank=True)
    fecha_nacimiento = models.DateField("Fecha de Nacimiento", null=True, blank=True)
    domicilio = models.CharField("Domicilio", max_length=255, blank=True)
    localidad = models.CharField("Localidad", max_length=150, blank=True)

    # Campos de Vida Marcial y Salud (Fase 2)
    fecha_ingreso_real = models.DateField("Fecha de Ingreso a la Asociación", null=True, blank=True)
    alergias = models.TextField("Alergias Conocidas", blank=True)
    condiciones_medicas = models.TextField("Condiciones Médicas", blank=True)
    contacto_emergencia_nombre = models.CharField("Nombre Contacto Emergencia", max_length=120, blank=True)
    contacto_emergencia_telefono = models.CharField("Teléfono Contacto Emergencia", max_length=50, blank=True)
    apto_medico = models.FileField("Certificado Apto Médico", upload_to="aptos_medicos/", null=True, blank=True)

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

    @property
    def antiguedad_anios(self):
        """Calcula los años de antigüedad en la asociación."""
        from datetime import date
        inicio = self.fecha_ingreso_real or self.date_joined.date()
        hoy = date.today()
        # Resta 1 si el mes/día actual es anterior al de inicio
        anios = hoy.year - inicio.year - ((hoy.month, hoy.day) < (inicio.month, inicio.day))
        return anios

    @property
    def estado_morosidad(self):
        """
        Calcula el estado de morosidad:
        'al_dia' -> Tiene pago de mes aprobado en el mes actual.
        'atrasado' -> No tiene pago, pero estamos entre el día 1 y 15 del mes.
        'vencido' -> No tiene pago, y pasamos el día 15.
        """
        from datetime import date
        hoy = date.today()
        # Buscamos si hay un pago de "mes" aprobado en este mes actual
        pago_mes_actual = self.pagos.filter(
            tipo=self.pagos.model.TipoPago.MES,
            estado=self.pagos.model.EstadoPago.APROBADO,
            fecha_registro__year=hoy.year,
            fecha_registro__month=hoy.month
        ).exists()

        if pago_mes_actual:
            return "al_dia"
        
        if hoy.day <= 15:
            return "atrasado"
        return "vencido"

    @property
    def color_estado(self):
        estado = self.estado_morosidad
        if estado == "al_dia": return "green"
        if estado == "atrasado": return "yellow"
        return "red"


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


class Examen(models.Model):
    """
    Registro de la línea de tiempo de graduaciones del alumno.
    """
    alumno = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="examenes")
    grado = models.CharField("Grado Alcanzado", max_length=100)
    fecha = models.DateField("Fecha del Examen")
    examinador = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="examenes_tomados")
    observaciones = models.TextField("Observaciones / Detalles", blank=True)

    class Meta:
        verbose_name = "Examen / Graduación"
        verbose_name_plural = "Exámenes y Graduaciones"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.alumno.nombre_completo} - {self.grado} ({self.fecha})"


class Horario(models.Model):
    """
    Día y hora de una clase.
    """
    class DiasSemana(models.TextChoices):
        LUNES = "LU", "Lunes"
        MARTES = "MA", "Martes"
        MIERCOLES = "MI", "Miércoles"
        JUEVES = "JU", "Jueves"
        VIERNES = "VI", "Viernes"
        SABADO = "SA", "Sábado"
        DOMINGO = "DO", "Domingo"

    dia = models.CharField(max_length=2, choices=DiasSemana.choices)
    hora_inicio = models.TimeField()
    hora_fin = models.TimeField()

    class Meta:
        verbose_name = "Horario"
        verbose_name_plural = "Horarios"
        ordering = ["dia", "hora_inicio"]

    def __str__(self):
        return f"{self.get_dia_display()} - {self.hora_inicio.strftime('%H:%M')} a {self.hora_fin.strftime('%H:%M')}"


class ClaseProgramada(models.Model):
    """
    El 'corazón' del sistema Marketplace: Vincula Profe + Actividad + Sede + Horario.
    """
    profesor = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name="clases_dictadas",
        limit_choices_to={'es_profe': True}
    )
    actividad = models.ForeignKey(
        Actividad,
        on_delete=models.CASCADE,
        related_name="clases_asignadas"
    )
    locacion = models.ForeignKey(
        Locacion,
        on_delete=models.CASCADE,
        related_name="clases_asignadas"
    )
    horarios = models.ManyToManyField(Horario, related_name="clases_asignadas")

    class Meta:
        verbose_name = "Clase Programada"
        verbose_name_plural = "Clases Programadas"

    def __str__(self):
        return f"{self.actividad.nombre} en {self.locacion.nombre} - Prof. {self.profesor.nombre_completo}"


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
    clase_programada = models.ForeignKey(
        ClaseProgramada,
        on_delete=models.SET_NULL,
        related_name="pagos",
        null=True,
        blank=True,
        help_text="Clase específica a la cual pertenece este pago (Sede + Actividad + Horario)."
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
    mercado_pago_id = models.CharField(max_length=255, null=True, blank=True)
    mercado_pago_status = models.CharField(max_length=50, null=True, blank=True)
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


# =========================================================
# FASE 3: Tienda "E-Commerce" LongHuHe (Equipamiento)
# =========================================================

class CategoriaProducto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = "Categoría de Producto"
        verbose_name_plural = "Categorías de Productos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    categoria = models.ForeignKey(CategoriaProducto, on_delete=models.CASCADE, related_name="productos")
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    activo = models.BooleanField(default=True, help_text="Si es Falso, se oculta de la tienda")
    permite_backorder = models.BooleanField(default=False, help_text="Permitir comprar aunque el stock sea 0")
    
    # Múltiples fotos para la ficha del producto
    foto1 = models.ImageField(upload_to="tienda/", blank=True, null=True)
    foto2 = models.ImageField(upload_to="tienda/", blank=True, null=True)
    foto3 = models.ImageField(upload_to="tienda/", blank=True, null=True)
    foto4 = models.ImageField(upload_to="tienda/", blank=True, null=True)
    foto5 = models.ImageField(upload_to="tienda/", blank=True, null=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    @property
    def hay_stock(self):
        return self.stock > 0

    @property
    def se_puede_comprar(self):
        return self.activo and (self.hay_stock or self.permite_backorder)


class Pedido(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "pendiente", "Pendiente de Pago/Conf"
        PAGADO = "pagado", "Pagado - A Preparar"
        ENTREGADO = "entregado", "Entregado"
        CANCELADO = "cancelado", "Cancelado"

    alumno = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="pedidos_tienda")
    fecha_registro = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.PENDIENTE)
    
    # Montos y Pago
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    metodo_pago = models.CharField(max_length=20, choices=Pago.MetodoPago.choices)
    cuotas = models.IntegerField(default=1)
    comprobante = models.FileField(upload_to="comprobantes_pedidos/", blank=True, null=True)
    
    # Integración Mercado Pago Central
    mercado_pago_id = models.CharField(max_length=255, null=True, blank=True)
    mercado_pago_status = models.CharField(max_length=50, null=True, blank=True)
    
    # Comisiones (Balance Vivo)
    profesor_venta = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True, 
        related_name="ventas_tienda_generadas",
        limit_choices_to={'es_profe': True},
        help_text="Profesor que recibirá comisión por esta venta."
    )
    porcentaje_comision = models.DecimalField(
        max_digits=5, decimal_places=2, default=0, help_text="% de ganancia para el profesor"
    )
    monto_comision = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, help_text="Calculado automáticamente"
    )
    backorder = models.BooleanField(
        default=False, help_text="Algún producto se compró sin stock y requiere reposición rápida"
    )

    class Meta:
        verbose_name = "Pedido de Tienda"
        verbose_name_plural = "Pedidos de Tienda"
        ordering = ["-fecha_registro"]

    def __str__(self):
        return f"Pedido #{self.id} - {self.alumno.nombre_completo} - {self.get_estado_display()}"


class PedidoItem(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey(Producto, on_delete=models.RESTRICT)
    cantidad = models.IntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = "Item de Pedido"
        verbose_name_plural = "Items de Pedido"

    def __str__(self):
        return f"{self.cantidad}x {self.producto.nombre} (Pedido #{self.pedido.id})"


# =========================================================
# FASE 4: Academia Digital (Biblioteca)
# =========================================================

class CategoriaContenido(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)

    class Meta:
        verbose_name = "Categoría de Contenido"
        verbose_name_plural = "Categorías de Contenido"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class NivelAcceso(models.TextChoices):
    TODOS = "todos", "Público / Todos los Alumnos"
    PRINCIPIANTE = "principiante", "Solo Principiantes y superior"
    INTERMEDIO = "intermedio", "Solo Intermedios y superior"
    AVANZADO = "avanzado", "Solo Avanzados / Maestros"


class Documento(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    categoria = models.ForeignKey(CategoriaContenido, on_delete=models.SET_NULL, null=True, blank=True, related_name="documentos")
    archivo = models.FileField(upload_to="biblioteca/documentos/")
    descargable = models.BooleanField(default=False, help_text="Si es Falso, el alumno solo podrá verlo en la app sin un botón de descarga expuesto.")
    nivel_acceso = models.CharField(max_length=20, choices=NivelAcceso.choices, default=NivelAcceso.TODOS)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Documento"
        verbose_name_plural = "Documentos"
        ordering = ["-fecha_subida"]

    def __str__(self):
        return self.titulo


class VideoTutorial(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    categoria = models.ForeignKey(CategoriaContenido, on_delete=models.SET_NULL, null=True, blank=True, related_name="videos")
    youtube_id = models.CharField(max_length=50, help_text="ID del video de YouTube (ej. dQw4w9WgXcQ de https://www.youtube.com/watch?v=dQw4w9WgXcQ)")
    nivel_acceso = models.CharField(max_length=20, choices=NivelAcceso.choices, default=NivelAcceso.TODOS)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Video Tutorial"
        verbose_name_plural = "Videos Tutoriales"
        ordering = ["-fecha_subida"]

    def __str__(self):
        return self.titulo
