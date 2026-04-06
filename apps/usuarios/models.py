import uuid
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver

class NivelAcceso(models.TextChoices):
    ALUMNO = "alumno", "Alumnos (Todos)"
    PRINCIPIANTE = "principiante", "Principiantes"
    AVANZADO = "avanzado", "Avanzados"
    INSTRUCTOR = "instructor", "Instructores"
    PROFESOR = "profesor", "Profesores"
    MAESTRO = "maestro", "Maestros"

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
        db_table = 'core_grado' # Link to existing table
        
    def __str__(self):
        return self.nombre

class Usuario(AbstractUser):
    # Opcionalmente ocultamos first_name y last_name heredados para evitar duplicidad
    first_name = None
    last_name = None

    nombre = models.CharField(max_length=120)
    apellido = models.CharField(max_length=120)
    celular = models.CharField(max_length=30, unique=True)
    sede = models.ForeignKey(
        'academia.Sede', # Referencia Lazy a la nueva app academia
        on_delete=models.PROTECT,
        related_name="usuarios",
        null=True,
    )
    grado = models.ForeignKey(
        Grado,
        on_delete=models.SET_NULL,
        related_name="alumnos",
        null=True,
        blank=True,
        verbose_name="Grado / Faja Actual"
    )
    es_profe = models.BooleanField(default=False)
    foto_perfil = models.ImageField("Foto de Perfil", upload_to="perfiles/", null=True, blank=True)

    # Campos de Mercado Pago para Profesores (Marketplace)
    mp_access_token = models.CharField("MP Access Token", max_length=500, blank=True, null=True)
    mp_public_key = models.CharField("MP Public Key", max_length=500, blank=True, null=True)

    # Nuevos campos para adultos mayores
    dni = models.CharField("DNI", max_length=15, blank=True)
    fecha_nacimiento = models.DateField("Fecha de Nacimiento", null=True, blank=True)
    domicilio = models.CharField("Domicilio", max_length=255, blank=True)
    localidad = models.CharField("Localidad", max_length=150, blank=True)

    # Campos de Vida Marcial y Salud (Fase 2)
    fecha_ingreso_real = models.DateField("Fecha de Ingreso a la Asociación", null=True, blank=True)
    alergias = models.TextField("Alergias Conocidas", blank=True, default="")
    condiciones_medicas = models.TextField("Condiciones Médicas", blank=True, default="")
    contacto_emergencia_nombre = models.CharField("Nombre Contacto Emergencia", max_length=120, blank=True, default="")
    contacto_emergencia_telefono = models.CharField("Teléfono Contacto Emergencia", max_length=50, blank=True, default="")
    contacto_emergencia_direccion = models.CharField("Dirección Contacto Emergencia", max_length=200, blank=True, default="")
    apto_medico = models.FileField("Certificado Apto Médico", upload_to="aptos_medicos/", null=True, blank=True)

    actividades = models.ManyToManyField('academia.Actividad', blank=True, related_name="alumnos")
    
    # --- ERP / Gestión de Asistencia y Pagos ---
    uuid_carnet = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    fecha_vencimiento_cuota = models.DateField("Fecha de Vencimiento de Cuota", null=True, blank=True)
    clases_disponibles = models.PositiveIntegerField("Clases Disponibles (Paquetes)", default=0)
    fecha_prorroga = models.DateField("Vencimiento de Prórroga", null=True, blank=True, help_text="Si solicita prórroga, tiene acceso hasta esta fecha.")

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

    qr_base64_cache = models.TextField(blank=True, null=True, help_text="Caché del código QR en base64 para evitar regenerarlo en memoria repetidamente.")

    class Meta:
        db_table = 'core_usuario' # Link to existing table

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
        
        # Comprobamos si este usuario es delegado activo de alguien más
        es_delegado_activo = False
        if self.pk:
            es_delegado_activo = Usuario.objects.filter(
                tesorero_autorizado=self, 
                autorizacion_tesoreria_activa=True
            ).exists()

        if any(roles_granulares) or es_delegado_activo:
            self.is_staff = True
        
        # 3. Auto-generación de Username válido (sin espacios ni caracteres raros)
        if not self.username and self.celular:
            import re
            clean_username = re.sub(r'[^a-zA-Z0-9@\.\+\-_]', '', self.celular)
            if not clean_username:
                clean_username = f"u_{uuid.uuid4().hex[:8]}"
            self.username = clean_username[:150]
        
        # 4. Auto-generación inteligente del QR cacheado (solo si está vacío)
        if not self.qr_base64_cache and self.uuid_carnet:
            import qrcode
            import io
            import base64
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(str(self.uuid_carnet))
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            self.qr_base64_cache = f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"

        super().save(*args, **kwargs)

    def __str__(self):
        rol = "Profesor" if self.es_profe else "Alumno"
        apellido = self.apellido or "Sin Apellido"
        nombre = self.nombre or "Sin Nombre"
        celular = self.celular or "---"
        return f"{apellido}, {nombre} ({rol}) - {celular}"

    @property
    def generar_qr_base64(self):
        """ Retorna el QR desde el caché en DB. Si por algún motivo está vacío, invoca un resave silencioso. """
        if self.qr_base64_cache:
            return self.qr_base64_cache
        
        # Fallback de recuperación de sistema (Solo ocurrirá la primera vez antes de migrar)
        # Se genera al vuelo sin necesidad de hacer save() explícito aquí para no causar recursiones.
        import qrcode
        import io
        import base64
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(str(self.uuid_carnet))
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"

    @property
    def alerta_inasistencia(self):
        """ Retorna True si el alumno no registra asistencias hace mas de 15 dias. """
        ultima = self.asistencias.order_by('-fecha_hora').first()
        if not ultima:
            return True
        return (timezone.now() - ultima.fecha_hora).days > 15

    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}".strip()

    @property
    def antiguedad_anios(self):
        from datetime import date
        inicio = self.fecha_ingreso_real or self.date_joined.date()
        hoy = date.today()
        anios = hoy.year - inicio.year - ((hoy.month, hoy.day) < (inicio.month, inicio.day))
        return anios

    @property
    def estado_morosidad(self):
        from datetime import date
        hoy = date.today()
        
        if not self.fecha_vencimiento_cuota:
            # Import circular? No, Pago está en ventas, lo importamos aquí localmente
            from apps.ventas.models import Pago
            pago_mes_actual = Pago.objects.filter(
                alumno=self,
                tipo=Pago.TipoPago.MES,
                estado=Pago.EstadoPago.APROBADO,
                fecha_registro__year=hoy.year,
                fecha_registro__month=hoy.month
            ).exists()
            if pago_mes_actual:
                return "al_dia"
            return "vencido"

        if hoy <= self.fecha_vencimiento_cuota:
            return "al_dia"
        
        from datetime import timedelta
        if hoy <= (self.fecha_vencimiento_cuota + timedelta(days=5)):
            return "atrasado"
            
        return "vencido"

    @property
    def color_estado(self):
        estado = self.estado_morosidad
        if estado == "al_dia":
            return "green"
        if estado == "atrasado":
            return "yellow"
        return "red"

class Examen(models.Model):
    """
    Registro de la línea de tiempo de graduaciones del alumno.
    """
    alumno = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name="examenes")
    grado = models.ForeignKey(Grado, on_delete=models.PROTECT, related_name="examenes_obtenidos")
    fecha = models.DateField("Fecha del Examen")
    examinador = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, blank=True, related_name="examenes_tomados")
    examinador_externo = models.CharField("Maestro Invitado (si no está en la app)", max_length=150, blank=True, default="")
    observaciones = models.TextField("Observaciones / Detalles", blank=True)

    class Meta:
        verbose_name = "Examen / Graduación"
        verbose_name_plural = "03.2 - Exámenes y Graduaciones"
        ordering = ["-fecha"]
        db_table = 'core_examen' # Link to existing table

    def __str__(self):
        try:
            alumno_str = self.alumno.nombre_completo if self.alumno else "Alumno desconocido"
            grado_str = self.grado.nombre if self.grado else "N/A"
            return f"{alumno_str} - {grado_str} ({self.fecha})"
        except Exception:
            return f"Examen #{self.id}"

# ==========================================
# SEÑALES DE LIMPIEZA DE ALMACENAMIENTO (S3)
# ==========================================
@receiver(post_delete, sender=Usuario)
def auto_delete_file_on_delete(sender, instance, **kwargs):
    """ Borra el archivo de S3 cuando se elimina el registro. """
    if instance.foto_perfil:
        if hasattr(instance.foto_perfil, 'delete'):
            instance.foto_perfil.delete(save=False)

@receiver(pre_save, sender=Usuario)
def auto_delete_file_on_change(sender, instance, **kwargs):
    """ Borra el archivo viejo de S3 cuando se reemplaza por uno nuevo. """
    if not instance.pk:
        return False
    try:
        old_file = Usuario.objects.get(pk=instance.pk).foto_perfil
    except Usuario.DoesNotExist:
        return False

    new_file = instance.foto_perfil
    if not old_file == new_file and old_file:
        if hasattr(old_file, 'delete'):
            old_file.delete(save=False)
