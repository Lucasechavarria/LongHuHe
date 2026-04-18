import os
import django
import sys

# Add current directory to path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.usuarios.models import Usuario

print("Usuarios en PRODUCCION (Supabase):")
users = Usuario.objects.filter(is_superuser=True)
for u in users:
    print(f"Username: {u.username}, Email: {u.email}, ID: {u.id}, Is Superuser: {u.is_superuser}")
