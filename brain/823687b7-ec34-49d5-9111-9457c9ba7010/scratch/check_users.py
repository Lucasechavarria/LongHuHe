import os
import sys
import django

sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.usuarios.models import Usuario

superusers = Usuario.objects.filter(is_superuser=True)
if superusers.exists():
    print("Superusuarios encontrados:")
    for user in superusers:
        print(f"Username: {user.username}, Email: {user.email}")
else:
    print("No se encontraron superusuarios.")
