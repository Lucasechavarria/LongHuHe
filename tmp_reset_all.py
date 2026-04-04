import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.usuarios.models import Usuario

def reset_all_admins():
    admins = [
        {'id': 4, 'username': 'asociacion'},
        {'id': 5, 'username': 'danielechavarria'},
        {'id': 7, 'username': 'lucasechavarria'}
    ]
    for data in admins:
        u = Usuario.objects.filter(id=data['id']).first()
        if u:
            u.username = data['username']
            u.set_password('Lucas2026!')
            u.is_active = True
            u.is_staff = True
            u.is_superuser = True
            u.rol_acceso_total = True
            u.save()
            print(f"DEBUG: Reset successful for {u.username}")
        else:
            print(f"DEBUG: User {data['id']} not found.")

if __name__ == "__main__":
    reset_all_admins()
