import io
import uuid
import qrcode
from PIL import Image
from django.core.files.base import ContentFile
from django.db.models import Q
from datetime import date, timedelta
from apps.usuarios.models import Usuario, Grado

class MediaService:
    """
    Servicio encargado del procesamiento de imágenes (optimizaciones y generación de QRs).
    Desacopla operaciones costosas del método de guardado de los modelos.
    """

    @staticmethod
    def generar_qr_fisico(usuario):
        """ Genera y asigna un archivo QR al usuario si tiene un uuid_carnet. """
        if not usuario.uuid_carnet:
            return False

        # Si ya existe y queremos regenerarlo explícitamente, debemos borrar el anterior
        if usuario.qr_image:
            usuario.qr_image.delete(save=False)

        qr = qrcode.QRCode(version=1, box_size=10, border=2)
        qr.add_data(str(usuario.uuid_carnet))
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        buffer = io.BytesIO()
        img.save(buffer)
        
        file_name = f"qr_{usuario.pk or uuid.uuid4().hex[:8]}.png"
        usuario.qr_image.save(file_name, ContentFile(buffer.getvalue()), save=False)
        return True

    @staticmethod
    def optimizar_foto_perfil(usuario):
        """ 
        Convierte la foto de perfil del usuario a formato WebP. 
        """
        if not usuario.foto_perfil or usuario.foto_perfil.name.endswith('.webp'):
            return False
            
        try:
            img = Image.open(usuario.foto_perfil)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            thumb_io = io.BytesIO()
            img.save(thumb_io, 'WEBP', quality=85)
            
            # Formatear nuevo nombre (sin extensión original + .webp)
            original_name = usuario.foto_perfil.name.split('/')[-1]
            new_name = original_name.rsplit('.', 1)[0] + '.webp'
            
            # Reemplazar archivo sin triggerear el .save() de la BD
            usuario.foto_perfil.save(new_name, ContentFile(thumb_io.getvalue()), save=False)
            return True
        except Exception as e:
            print(f"ERROR CRITICO al optimizar imagen: {str(e)}")
            return False


class UsuarioService:
    """
    Servicio de Dominio para manejar procesos de negocio de Usuarios y Alumnos.
    """

    @staticmethod
    def crear_alumno_desde_onboarding(datos, foto_perfil=None):
        """
        Crea o actualiza un alumno desde el formulario de Onboarding.
        Retorna la instancia del Usuario.
        """
        celular = datos['celular']
        dni = datos['dni']
        
        default_grado = Grado.objects.filter(Q(nombre__iexact="Blanco") | Q(orden=0)).first()

        usuario, created = Usuario.objects.get_or_create(
            celular=celular,
            defaults={
                'nombre': datos['nombre'],
                'apellido': datos['apellido'],
                'dni': dni,
                'fecha_nacimiento': datos['fecha_nacimiento'],
                'domicilio': datos['domicilio'],
                'localidad': datos['localidad'],
                'sede': datos['sede'],
                'foto_perfil': foto_perfil,
                'grado': default_grado,
            }
        )
        
        if not created:
            usuario.nombre = datos['nombre']
            usuario.apellido = datos['apellido']
            usuario.dni = dni
            usuario.fecha_nacimiento = datos['fecha_nacimiento']
            usuario.domicilio = datos['domicilio']
            usuario.localidad = datos['localidad']
            usuario.sede = datos['sede']
            if not usuario.grado:
                usuario.grado = default_grado
            if foto_perfil:
                usuario.foto_perfil = foto_perfil
            
        actividad = datos.get('actividad_inicial')
        
        # Guardado del usuario
        # Optimizamos imagen y QR antes de guardar para no hacerlo dentro del save()
        if foto_perfil:
            MediaService.optimizar_foto_perfil(usuario)
            
        if not usuario.qr_image:
            MediaService.generar_qr_fisico(usuario)
            
        usuario.save()

        if actividad:
            usuario.actividades.add(actividad)

        return usuario

    @staticmethod
    def solicitar_prorroga(alumno):
        """
        Lógica de negocio para otorgar una prórroga de 15 días a un alumno moroso.
        Retorna True si fue exitoso, False si ya solicitó prórroga este mes.
        """
        if alumno.estado_morosidad != 'vencido':
            return False, "No necesitas prórroga, tu cuota está al día."

        hoy = date.today()
        
        # Validación de "Una sola prórroga por mes"
        if (alumno.ultima_prorroga_solicitada and 
            alumno.ultima_prorroga_solicitada.month == hoy.month and 
            alumno.ultima_prorroga_solicitada.year == hoy.year):
            return False, "Ya has solicitado una prórroga este mes. Por favor, regulariza tu cuota para continuar."

        # Otorgamos 15 días desde hoy
        alumno.fecha_prorroga = hoy + timedelta(days=15)
        alumno.ultima_prorroga_solicitada = hoy
        alumno.save(update_fields=['fecha_prorroga', 'ultima_prorroga_solicitada'])
        
        return True, "Prórroga de 15 días activada. Tenés acceso completo temporariamente."
