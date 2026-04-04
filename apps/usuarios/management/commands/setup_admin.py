from django.core.management.base import BaseCommand
from apps.usuarios.models import Usuario

class Command(BaseCommand):
    help = 'Crea un superusuario master si no existe'

    def handle(self, *args, **options):
        if not Usuario.objects.filter(username='admin').exists():
            Usuario.objects.create_superuser(
                username='admin',
                email='admin@example.com',
                password='admin123',
                celular='1122334455',
                nombre='Master',
                apellido='Dojo'
            )
            self.stdout.write(self.style.SUCCESS('Superuser creado: admin / admin123'))
        else:
            self.stdout.write(self.style.WARNING('El superuser ya existe.'))
