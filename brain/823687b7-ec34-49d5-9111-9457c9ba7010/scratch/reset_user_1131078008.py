import os
import sys
import django

sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.usuarios.models import Usuario

user = Usuario.objects.filter(username='1131078008').first()
if user:
    user.set_password('admin123')
    user.save()
    print("Password para '1131078008' reseteada a 'admin123'")
else:
    print("No se encontro el usuario '1131078008'")
