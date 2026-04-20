import uuid
from django.utils import timezone
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_delete, pre_save
from django.dispatch import receiver
from django.utils.functional import cached_property

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
    
    costo_examen = models.DecimalField("Costo de Examen", max_digits=10, decimal_places=2, default=0)
    
    class Meta:
        verbose_name = "Escala de Grados"
        verbose_name_plural = "03.1 - Escala de Grados / Fajas"
        ordering = ["orden"]
        db_table = 'core_grado' # Link to existing table
        
    def __str__(self):
        return self.nombre_formateado

    @property
    def nombre_formateado(self):
        """ 
        Retorna el nombre del grado formateado (ej: Negro 1 -> I Tuan).
        """
        import re
        # Buscar patrón "Negro [numero]"
        match = re.search(r'Negro\s*(\d+)', self.nombre, re.IGNORECASE)
        if match:
            nivel = int(match.group(1))
            # Usar la función estática de conversión (definida en Usuario o moverla aquí)
            romano = self.int_to_roman(nivel)
            return f"{romano} Thuan"
        
        # Si es solo "Negro"
        if "Negro" in self.nombre.strip():
            return "Cinto Negro"

        return self.nombre

    @staticmethod
    def int_to_roman(n):
        """ Convierte enteros a números romanos (hasta 10). """
        romanos = {1: 'I', 2: 'II', 3: 'III', 4: 'IV', 5: 'V', 6: 'VI', 7: 'VII', 8: 'VIII', 9: 'IX', 10: 'X'}
        return romanos.get(n, str(n))

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
    nivel_acceso = models.CharField(
        "Nivel de Acceso Academia", 
        max_length=20, 
        choices=NivelAcceso.choices, 
        default=NivelAcceso.ALUMNO,
        help_text="Determina qué contenido de la biblioteca puede ver el alumno."
    )
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
    
    # --- BECAS ---
    es_becado = models.BooleanField(
        "Es Becado", default=False,
        help_text="Si está activo, el alumno tiene exención total de cuota. No necesita registrar pagos mensuales."
    )
    motivo_beca = models.CharField(
        "Motivo de Beca", max_length=255, blank=True, default="",
        help_text="Ej: Hijo del instructor, Situación económica, Beca de rendimiento."
    )

    # --- ERP / Gestión de Asistencia y Pagos ---
    uuid_carnet = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    fecha_vencimiento_cuota = models.DateField("Fecha de Vencimiento de Cuota", null=True, blank=True)
    dia_corte_cuota = models.PositiveSmallIntegerField(
        "Día de Corte de Cuota", default=0,
        help_text="Día del mes en que vence la cuota del alumno (Ej: 5 = vence el día 5 de cada mes). "
                  "0 = se usa el día actual del primer pago. Se asigna automáticamente al aprobar el primer pago."
    )
    clases_disponibles = models.PositiveIntegerField("Clases Disponibles (Paquetes)", default=0)
    fecha_prorroga = models.DateField(
        "Vencimiento de Prórroga", null=True, blank=True,
        help_text="Si solicita prórroga, tiene acceso de asistencia hasta esta fecha. Solo 1 por período de cuota."
    )
    ultima_prorroga_solicitada = models.DateField(
        "Última Prórroga Solicitada", null=True, blank=True,
        help_text="Fecha en que se solicitó la última prórroga. Se usa para limitar a una por mes."
    )

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

    qr_image = models.ImageField("Código QR", upload_to="qrs/", null=True, blank=True)
    qr_base64_cache = models.TextField(blank=True, null=True, help_text="[DEPRECATED] Usar qr_image en su lugar.")

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
        
        # 4. Generación de QR físico (Optimización Sprint 8 + Audit Sprint 9)
        uuid_cambio = False
        if self.pk:
            old_inst = Usuario.objects.filter(pk=self.pk).values('uuid_carnet', 'qr_image').first()
            if old_inst and old_inst['uuid_carnet'] != self.uuid_carnet:
                uuid_cambio = True
                if old_inst['qr_image']:
                    self.qr_image.delete(save=False)

        if (not self.qr_image or uuid_cambio) and self.uuid_carnet:
            import qrcode
            import io
            from django.core.files.base import ContentFile
            
            qr = qrcode.QRCode(version=1, box_size=10, border=2)
            qr.add_data(str(self.uuid_carnet))
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            
            file_name = f"qr_{self.pk or uuid.uuid4().hex[:8]}.png"
            # NO llamamos a .save() del campo aquí para evitar interferencias con el super().save()
            # Simplemente asignamos el contenido
            self.qr_image.save(file_name, ContentFile(buffer.getvalue()), save=False)

        # 5. Optimización de Foto de Perfil (WebP) (Task - Visuals)
        if not getattr(self, '_img_optimized', False):
            if self.foto_perfil and not self.foto_perfil.name.endswith('.webp'):
                from PIL import Image
                import io
                from django.core.files.base import ContentFile
                try:
                    img = Image.open(self.foto_perfil)
                    if img.mode in ("RGBA", "P"):
                        img = img.convert("RGB")
                    thumb_io = io.BytesIO()
                    img.save(thumb_io, 'WEBP', quality=85)
                    new_name = self.foto_perfil.name.split('.')[0] + '.webp'
                    
                    # Marcamos como optimizado ANTES para evitar bucles si decidimos usar save=True
                    self._img_optimized = True
                    self.foto_perfil.save(new_name, ContentFile(thumb_io.getvalue()), save=False)
                    print(f"ÉXITO: Imagen subida a S3 -> {self.foto_perfil.name}")
                except Exception as e:
                    print(f"ERROR CRITICO en subida a S3: {str(e)}")
                    self._img_optimized = True 
            else:
                self._img_optimized = True
        
        # 6. Sincronización de Nivel de Acceso con Grado (Audit de Coherencia)
        if self.grado and self.grado.nivel_desbloqueado:
            self.nivel_acceso = self.grado.nivel_desbloqueado

        super().save(*args, **kwargs)

    def __str__(self):
        rol = "Profesor" if self.es_profe else "Alumno"
        apellido = self.apellido or "Sin Apellido"
        nombre = self.nombre or "Sin Nombre"
        celular = self.celular or "---"
        return f"{apellido}, {nombre} ({rol}) - {celular}"

    @property
    def generar_qr_base64(self):
        """ Retorna el QR en formato data URI base64 para embeber en HTML/PDF. """
        # Prioridad 1: Cache en base64 (muy rápido)
        if self.qr_base64_cache:
             if self.qr_base64_cache.startswith('data:image'):
                 return self.qr_base64_cache
             return f"data:image/png;base64,{self.qr_base64_cache}"
        
        # Prioridad 2: Si no hay cache, intentar generar sobre la marcha si hay UUID
        if self.uuid_carnet:
            import qrcode
            import io
            import base64
            qr = qrcode.QRCode(version=1, box_size=10, border=2)
            qr.add_data(str(self.uuid_carnet))
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            encoded_string = base64.b64encode(buffer.getvalue()).decode('utf-8')
            return f"data:image/png;base64,{encoded_string}"
        
        return ""

    @property
    def grado_nombre(self):
        """ 
        Retorna el nombre del grado formateado del alumno. 
        Si no tiene grado, retorna Blanco.
        """
        if not self.grado:
            return "Blanco"
        return self.grado.nombre_formateado

    @property
    def alerta_inasistencia(self):
        """ 
        Retorna True si el alumno no registra asistencias hace mas de 15 dias. 
        """
        ultima = self.asistencias.order_by('-fecha_hora').first()
        from datetime import timedelta
        hoy = timezone.now()
        
        if not ultima:
            # Requerimiento de QA: Alumno sin asistencias = Alerta.
            return True
        
        return (hoy - ultima.fecha_hora) > timedelta(days=15)

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

    @cached_property
    def estado_morosidad(self):
        from datetime import date
        hoy = date.today()

        # 1. Alumnos becados: exentos de cuota, siempre al día.
        if self.es_becado:
            return "becado"

        # 2. Sin fecha de vencimiento aún (alumno nuevo o sin primer pago aprobado)
        if not self.fecha_vencimiento_cuota:
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

        # 3. Cuota vigente
        if hoy <= self.fecha_vencimiento_cuota:
            return "al_dia"

        # 4. Dentro del período de gracia (5 días)
        from datetime import timedelta
        if hoy <= (self.fecha_vencimiento_cuota + timedelta(days=5)):
            return "atrasado"

        # 5. Cuota vencida pero con prórroga activa
        if self.fecha_prorroga and hoy <= self.fecha_prorroga:
            return "prorroga"

        # 6. Vencida sin prórroga o prórroga expirada
        return "vencido"

    @property
    def color_estado(self):
        estado = self.estado_morosidad
        colores = {
            "becado":   "#3b82f6",  # Azul
            "al_dia":  "#22c55e",  # Verde
            "atrasado": "#f97316",  # Naranja
            "prorroga": "#a855f7",  # Púrpura
            "vencido":  "#ef4444",  # Rojo
        }
        return colores.get(estado, "#6b7280")

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

@receiver(pre_save, sender=Usuario)
def sincronizar_nivel_acceso_con_grado(sender, instance, **kwargs):
    """
    Sincroniza el nivel_acceso del usuario basado en su grado.
    Permite carga inicial de alumnos graduados sin pasar por exámenes.
    """
    if instance.grado and instance.grado.nivel_desbloqueado:
        # Solo actualizamos si el nivel cambió o es una carga inicial
        if instance.nivel_acceso != instance.grado.nivel_desbloqueado:
            instance.nivel_acceso = instance.grado.nivel_desbloqueado
