import os
import django

# Setup django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.usuarios.models import Usuario

def reset_user():
    u = Usuario.objects.filter(id=7).first()
    if u:
        u.username = 'lucasechavarria'
        u.set_password('Lucas2026!')
        u.is_active = True
        u.is_staff = True
        u.is_superuser = True
        u.rol_acceso_total = True
        u.save()
        print(f"DEBUG: User updated. Username: {u.username}")
        print(f"DEBUG: Is Staff: {u.is_staff}")
        print(f"DEBUG: Is Active: {u.is_active}")
        print(f"DEBUG: Password verification: {u.check_password('Lucas2026!')}")
    else:
        print("DEBUG: User ID 7 not found.")

if __name__ == "__main__":
    reset_user()
