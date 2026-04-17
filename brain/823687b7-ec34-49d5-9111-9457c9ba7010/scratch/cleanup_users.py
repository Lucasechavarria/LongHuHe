import os
import sys
import django

sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.usuarios.models import Usuario

# 1. Eliminar admin
deleted_admin = Usuario.objects.filter(username='admin').delete()
if deleted_admin[0] > 0:
    print("Usuario 'admin' eliminado satisfactoriamente.")
else:
    print("No se encontro el usuario 'admin' para eliminar.")

# 2. Actualizar mi usuario (1131078008)
user = Usuario.objects.filter(username='1131078008').first()
if user:
    user.set_password('Anfaso12@')
    user.is_superuser = True
    user.is_staff = True
    # Asegurar roles ERP
    user.rol_acceso_total = True
    user.rol_gestion_alumnos = True
    user.rol_gestion_sedes = True
    user.rol_gestion_tienda = True
    user.rol_gestion_tesoreria = True
    user.rol_gestion_academia = True
    user.save()
    print(f"Usuario '{user.username}' actualizado: contraseña cambiada y permisos de superadmin asegurados.")
else:
    print("No se encontró el usuario '1131078008' para actualizar.")
