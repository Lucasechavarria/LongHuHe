import uuid
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class NivelAcceso(models.TextChoices):
    ALUMNO = "alumno", "Alumnos (Todos)"
    PRINCIPIANTE = "principiante", "Principiantes"
    AVANZADO = "avanzado", "Avanzados"
    INSTRUCTOR = "instructor", "Instructores"
    PROFESOR = "profesor", "Profesores"
    MAESTRO = "maestro", "Maestros"

class Sede(models.Model):
    """
    Lugar físico donde el maestro da clase (antes 'Locación').
    Ejemplos: 'Centro de Jubilados San Martín', 'Plaza Norte', etc.
    """
    nombre = models.CharField(max_length=120)
    # actividades = models.ManyToManyField("Actividad", related_name="sedes", blank=True) # REMOVED for simplicity
    mapa_url = models.URLField("Enlace Google Maps", max_length=500, blank=True, null=True)

    class Meta:
        verbose_name = "Sede"
        verbose_name_plural = "01.1 - Sedes"
        ordering = ["nombre"]

    @property
    def actividades(self):
        """
        Deduce las actividades que se dictan en esta sede a través del cronograma.
        Mantiene la compatibilidad con los templates que esperan 'sede.actividades.all'.
        """
        return Actividad.objects.filter(clases_asignadas__sede=self).distinct()

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
        verbose_name_plural = "01.2 - Actividades"

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
    sede = models.ForeignKey(
        Sede,
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
    
    # --- ERP / Gestión de Asistencia y Pagos ---
    uuid_carnet = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    fecha_vencimiento_cuota = models.DateField("Fecha de Vencimiento de Cuota", null=True, blank=True)

    # --- SEGURIDAD Y ROLES ERP (Fase Final) ---
    rol_acceso_total = models.BooleanField(
        "Acceso Total (Superadministrador)", default=False, 
        help_text="Control absoluto sobre toda la plataforma (Dios)."
    )
    rol_gestion_alumnos = models.BooleanField(
        "Gestión de Alumnos", default=False, 
        help_text="Inscripciones, morosidad, aptos médicos."
    )
    rol_gestion_sedes = models.BooleanField(
        "Gestión de Sedes", default=False, 
        help_text="Locaciones, clases, horarios, exámenes."
    )
    rol_gestion_tienda = models.BooleanField(
        "Gestión de Tienda", default=False, 
        help_text="Productos, stock, pedidos."
    )
    rol_gestion_tesoreria = models.BooleanField(
        "Gestión de Tesorería (Global)", default=False, 
        help_text="Todo el dinero de la asociación."
    )
    rol_gestion_academia = models.BooleanField(
        "Gestión de Academia", default=False, 
        help_text="Biblioteca de videos y documentos."
    )

    # --- SISTEMA DE DELEGACIÓN FINANCIERA ---
    tesorero_autorizado = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name="tesoreria_admin_de",
        verbose_name="Tesorero Autorizado (Delegado)",
        help_text="Persona que gestionará las comisiones de este profesor."
    )
    autorizacion_tesoreria_activa = models.BooleanField(
        "Autorización Tesorería Activa", default=False,
        help_text="Interruptor de seguridad. Si es falso, el delegado no podrá entrar al panel de tesorería."
    )

    def save(self, *args, **kwargs):
        # 1. Gestión de Superusuario (Acceso Total)
        if self.rol_acceso_total:
            self.is_staff = True
            self.is_superuser = True
        
        # 2. Gestión de Staff Granular
        roles_granulares = [
            self.rol_gestion_alumnos, self.rol_gestion_sedes, 
            self.rol_gestion_tienda, self.rol_gestion_tesoreria, 
            self.rol_gestion_academia
        ]
        
        # También comprobamos si este usuario es delegado activo de alguien más
        es_delegado_activo = False
        if self.pk:
            # Importamos aquí si fuera necesario prevenir circulares
            es_delegado_activo = Usuario.objects.filter(
                tesorero_autorizado=self, 
                autorizacion_tesoreria_activa=True
            ).exists()

        if any(roles_granulares) or es_delegado_activo:
            self.is_staff = True
        
        # 3. Seguridad: si no tiene nada de lo anterior, le quitamos el staff (a menos que sea admin nativo)
        # Nota: no le quitamos is_superuser si se puso manual por terminal
        
        super().save(*args, **kwargs)


    class Meta:
        verbose_name = "Usuario / Alumno / Profe"
        verbose_name_plural = "02.1 - Panel Maestro de Usuarios"
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
        Calcula el estado de morosidad basado en la fecha de vencimiento:
        'al_dia' -> Hoy <= fecha_vencimiento_cuota.
        'atrasado' -> Pasó el vencimiento, pero estamos dentro de los 5 días de gracia (opcional, por ahora 0).
        'vencido' -> Pasó el vencimiento.
        """
        from datetime import date
        hoy = date.today()
        
        if not self.fecha_vencimiento_cuota:
            # Si no tiene fecha, usamos la lógica anterior por defecto (mes actual)
            pago_mes_actual = self.pagos.filter(
                tipo=self.pagos.model.TipoPago.MES,
                estado=self.pagos.model.EstadoPago.APROBADO,
                fecha_registro__year=hoy.year,
                fecha_registro__month=hoy.month
            ).exists()
            if pago_mes_actual: return "al_dia"
            return "vencido"

        if hoy <= self.fecha_vencimiento_cuota:
            return "al_dia"
        
        # Margen de gracia de 5 días para 'atrasado'
        from datetime import timedelta
        if hoy <= (self.fecha_vencimiento_cuota + timedelta(days=5)):
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
        verbose_name_plural = "02.2 - Registro de Asistencias"
        ordering = ["-fecha_hora"]

    def __str__(self):
        fecha = self.fecha_hora.strftime("%d/%m/%Y %H:%M")
        return f"Asistencia de {self.alumno.nombre_completo} - {fecha}"


class Grado(models.Model):
    """
    Jerarquía de cintos / fajas (Blanco, Amarillo, Negro, etc.)
    Convertido a CRUD para que el usuario defina su propia escala.
    """
    nombre = models.CharField(max_length=100)
    orden = models.PositiveIntegerField(default=0, help_text="Para ordenar la jerarquía (ej. 0=Blanco, 1=Final)")
    
    nivel_desbloqueado = models.CharField(
        "Nivel de Acceso que Otorga", 
        max_length=20, 
        choices=NivelAcceso.choices, 
        default=NivelAcceso.PRINCIPIANTE,
        help_text="Al obtener este grado en un examen, el alumno desbloquea este nivel de contenido en la academia."
    )
    
    class Meta:
        verbose_name = "Escala de Grados"
        verbose_name_plural = "03.1 - Escala de Grados / Fajas"
        ordering = ["orden"]
        
    def __str__(self):
        return self.nombre


class Examen(models.Model):
    """
    Registro de la línea de tiempo de graduaciones del alumno.
    """
    alumno = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="examenes")
    grado = models.ForeignKey(Grado, on_delete=models.PROTECT, related_name="examenes_obtenidos")
    fecha = models.DateField("Fecha del Examen")
    examinador = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="examenes_tomados")
    examinador_externo = models.CharField("Maestro Invitado (si no está en la app)", max_length=150, blank=True)
    observaciones = models.TextField("Observaciones / Detalles", blank=True)

    class Meta:
        verbose_name = "Examen / Graduación"
        verbose_name_plural = "03.2 - Exámenes y Graduaciones"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.alumno.nombre_completo} - {self.grado.nombre} ({self.fecha})"


# El modelo Horario ha sido integrado directamente dentro de ClaseProgramada para simplificar la gestión.


class Cronograma(models.Model):
    """
    El 'corazón' de la agenda: Vincula Profe + Actividad + Sede + Horario.
    """
    class DiasSemana(models.TextChoices):
        LUNES = "LU", "Lunes"
        MARTES = "MA", "Martes"
        MIERCOLES = "MI", "Miércoles"
        JUEVES = "JU", "Jueves"
        VIERNES = "VI", "Viernes"
        SABADO = "SA", "Sábado"
        DOMINGO = "DO", "Domingo"

    profesor = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name="clases_dictadas",
        limit_choices_to={'es_profe': True}
    )
    profesor_asistente = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True, 
        related_name="clases_asistente",
        limit_choices_to={'es_profe': True}
    )
    actividad = models.ForeignKey(
        Actividad,
        on_delete=models.CASCADE,
        related_name="clases_asignadas"
    )
    sede = models.ForeignKey(
        Sede,
        on_delete=models.CASCADE,
        related_name="clases_asignadas"
    )
    
    # Horario integrado
    dia = models.CharField("Día de la semana", max_length=2, choices=DiasSemana.choices, default="LU")
    hora_inicio = models.TimeField("Hora de Inicio", null=True, blank=True)
    hora_fin = models.TimeField("Hora de Fin", null=True, blank=True)

    porcentaje_comision_asistente = models.DecimalField(
        " % Comisión Asistente", max_digits=5, decimal_places=2, default=0,
        help_text="Comisión que se lleva el asistente por las ventas registradas en esta clase."
    )

    class Meta:
        verbose_name = "Horario / Clase"
        verbose_name_plural = "01.3 - Cronograma de Clases"
        ordering = ["sede", "dia", "hora_inicio"]

    def __str__(self):
        horario_str = f"{self.get_dia_display()} {self.hora_inicio.strftime('%H:%M') if self.hora_inicio else '--:--'}"
        return f"{self.actividad.nombre} ({horario_str}) - {self.sede.nombre} - Prof. {self.profesor.nombre}"


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
        Cronograma,
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
        verbose_name = "Pago / Finanzas"
        verbose_name_plural = "02.3 - Pagos y Tesorería"
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
        verbose_name = "Producto: Categoría"
        verbose_name_plural = "04.2 - Tienda: Categorías (Configuración)"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    categoria = models.ForeignKey(CategoriaProducto, on_delete=models.CASCADE, related_name="productos")
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    activo = models.BooleanField(default=True, help_text="Si es Falso, se oculta de la tienda")
    permite_backorder = models.BooleanField(default=False, help_text="Permitir comprar aunque el stock sea 0")
    
    # Comisiones y Financiación (Solicitado por el usuario)
    cuotas_maximas = models.IntegerField("Cuotas Máximas", default=1)
    costo_reposicion = models.DecimalField(
        "Costo de Reposición", max_digits=10, decimal_places=2, default=0,
        help_text="Lo que le cuesta a la asociación reponer este producto."
    )
    porcentaje_comision = models.DecimalField(
        "Porcentaje de Comisión Profe", max_digits=5, decimal_places=2, default=0,
        help_text="Comisión que se lleva el profesor por vender este producto específico."
    )
    
    # Múltiples fotos para la ficha del producto

    foto1 = models.ImageField(upload_to="tienda/", blank=True, null=True)
    foto2 = models.ImageField(upload_to="tienda/", blank=True, null=True)
    foto3 = models.ImageField(upload_to="tienda/", blank=True, null=True)
    foto4 = models.ImageField(upload_to="tienda/", blank=True, null=True)
    foto5 = models.ImageField(upload_to="tienda/", blank=True, null=True)

    class Meta:
        verbose_name = "Producto: Ficha Central"
        verbose_name_plural = "04.1 - Tienda: Productos"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre

    @property
    def hay_stock(self):
        return self.variantes.filter(stock__gt=0).exists()

    @property
    def se_puede_comprar(self):
        return self.activo and (self.hay_stock or self.permite_backorder)


class ProductoVariante(models.Model):
    """
    Desglose por talle con stock independiente.
    """
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="variantes")
    talle = models.CharField(max_length=50)
    stock = models.IntegerField("Cantidad en Stock", default=0)

    class Meta:
        verbose_name = "Variante de Producto (Talle)"
        verbose_name_plural = "Variantes de Producto (Talles)"

    def __str__(self):
        return f"{self.producto.nombre} - Talle: {self.talle} (Stock: {self.stock})"


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
    
    # Trazabilidad y Desglose Financiero (ERP Premium)
    clase_origen = models.ForeignKey(
        Cronograma, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="pedidos_clase",
        help_text="Clase en la que se realizó la venta (Sede + Horario + Profe)."
    )
    
    monto_costo_reposicion = models.DecimalField(
        "Monto Costo Reposición", max_digits=10, decimal_places=2, default=0,
        help_text="Suma de los costos de los items vendidos."
    )
    monto_comision_asistente = models.DecimalField(
        "Monto Comisión Asistente", max_digits=10, decimal_places=2, default=0,
        help_text="Comisión para el profesor asistente de la clase origen."
    )
    utilidad_neta_asociacion = models.DecimalField(
        "Utilidad Neta Asociación", max_digits=10, decimal_places=2, default=0,
        help_text="Lo que queda en caja tras costos y comisiones."
    )

    backorder = models.BooleanField(
        default=False, help_text="Algún producto se compró sin stock y requiere reposición rápida"
    )

    class Meta:
        verbose_name = "Tienda: Pedido"
        verbose_name_plural = "04.3 - Tienda: Gestión de Pedidos"
        ordering = ["-fecha_registro"]

    def __str__(self):
        return f"Pedido #{self.id} - {self.alumno.nombre_completo} - {self.get_estado_display()}"

    def save(self, *args, **kwargs):
        # Al marcarse como pagado, calculamos rentabilidad
        if self.estado == self.Estado.PAGADO:
            # 1. Costo de Reposicion (basado en items)
            total_costo = 0
            for item in self.items.all():
                total_costo += (item.producto.costo_reposicion * item.cantidad)
            self.monto_costo_reposicion = total_costo
            
            # 2. Comisiones
            # Profe Principal (ya tiene profesor_venta y porcentaje_comision inicial)
            self.monto_comision = self.total * (self.porcentaje_comision / 100)
            
            # Asistente
            if self.clase_origen and self.clase_origen.profesor_asistente:
                pct_asistente = self.clase_origen.porcentaje_comision_asistente
                self.monto_comision_asistente = self.total * (pct_asistente / 100)
            else:
                self.monto_comision_asistente = 0
            
            # 3. Utilidad Neta Asociación
            self.utilidad_neta_asociacion = (
                self.total - self.monto_costo_reposicion - 
                self.monto_comision - self.monto_comision_asistente
            )
            
        super().save(*args, **kwargs)


class PedidoItem(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey(Producto, on_delete=models.RESTRICT)
    variante = models.ForeignKey(ProductoVariante, on_delete=models.SET_NULL, null=True, blank=True)
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
        verbose_name = "Academia: Categoría"
        verbose_name_plural = "05.1 - Academia: Materias Digitales"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre




class Documento(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    categoria = models.ForeignKey(CategoriaContenido, on_delete=models.SET_NULL, null=True, blank=True, related_name="documentos")
    archivo = models.FileField(upload_to="biblioteca/documentos/")
    descargable = models.BooleanField(default=False, help_text="Si es Falso, el alumno solo podrá verlo en la app sin un botón de descarga expuesto.")
    nivel_acceso = models.CharField(max_length=20, choices=NivelAcceso.choices, default=NivelAcceso.ALUMNO)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Academia: Documento"
        verbose_name_plural = "05.2 - Academia: Documentos (Oculto)"
        ordering = ["-fecha_subida"]

    def __str__(self):
        return self.titulo


class VideoTutorial(models.Model):
    titulo = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    categoria = models.ForeignKey(CategoriaContenido, on_delete=models.SET_NULL, null=True, blank=True, related_name="videos")
    youtube_id = models.CharField(max_length=50, help_text="ID del video de YouTube (ej. dQw4w9WgXcQ de https://www.youtube.com/watch?v=dQw4w9WgXcQ)")
    nivel_acceso = models.CharField(max_length=20, choices=NivelAcceso.choices, default=NivelAcceso.ALUMNO)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Academia: Video"
        verbose_name_plural = "05.3 - Academia: Videos (Oculto)"
        ordering = ["-fecha_subida"]

    def __str__(self):
        return self.titulo
