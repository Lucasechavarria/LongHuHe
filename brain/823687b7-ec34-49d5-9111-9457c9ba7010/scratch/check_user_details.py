import os
import sys
import django

sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.usuarios.models import Usuario

user = Usuario.objects.filter(username='1131078008').first()
if user:
    print(f"Usuario: {user.username}")
    print(f"Email: {user.email}")
    print(f"Is active: {user.is_active}")
    print(f"Is staff: {user.is_staff}")
    print(f"Is superuser: {user.is_superuser}")
    print(f"Es profe: {user.es_profe}")
    print(f"Rol acceso total: {user.rol_acceso_total}")
else:
    print("Usuario no encontrado")
