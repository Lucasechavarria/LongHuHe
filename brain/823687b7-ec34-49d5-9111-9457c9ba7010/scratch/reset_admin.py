import os
import sys
import django

sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.usuarios.models import Usuario

user = Usuario.objects.filter(username='admin').first()
if user:
    user.set_password('admin123')
    user.save()
    print("Password para 'admin' reseteada a 'admin123'")
else:
    print("No se encontro el usuario 'admin'")
