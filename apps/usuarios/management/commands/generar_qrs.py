import io
import qrcode
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from apps.usuarios.models import Usuario

class Command(BaseCommand):
    help = 'Genera archivos físicos de imagen QR para todos los usuarios que no los tengan.'

    def handle(self, *args, **options):
        usuarios = Usuario.objects.filter(qr_image__isnull=True) | Usuario.objects.filter(qr_image='')
        count = usuarios.count()
        
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No hay usuarios pendientes de generar QR.'))
            return

        self.stdout.write(f'Procesando {count} usuarios...')
        
        processed = 0
        for usuario in usuarios:
            if not usuario.uuid_carnet:
                continue
                
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(str(usuario.uuid_carnet))
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            buffer = io.BytesIO()
            img.save(buffer, format="PNG")
            
            file_name = f"qr_{usuario.id}.png"
            usuario.qr_image.save(file_name, ContentFile(buffer.getvalue()), save=True)
            processed += 1
            
        self.stdout.write(self.style.SUCCESS(f'Se generaron {processed} códigos QR exitosamente.'))
