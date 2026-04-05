import os
import django
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['FORCE_REMOTE_DB'] = 'True'
django.setup()

from apps.usuarios.models import Usuario

def force_reset():
    email = 'echavarrialucas1986@gmail.com'
    u = Usuario.objects.filter(email=email).first()
    if u:
        u.username = 'lucasechavarria'
        u.set_password('Lucas2026!')
        u.is_active = True
        u.is_staff = True
        u.is_superuser = True
        u.rol_acceso_total = True
        u.save()
        print(f"DONE: Reset by email {email}. Username is {u.username}")
    else:
        # Try finding by name
        u = Usuario.objects.filter(nombre='Lucas', apellido='Echavarria').first()
        if u:
            u.username = 'lucasechavarria'
            u.set_password('Lucas2026!')
            u.is_active = True
            u.is_staff = True
            u.is_superuser = True
            u.rol_acceso_total = True
            u.save()
            print(f"DONE: Reset by name. Username is {u.username}")
        else:
            print(f"NOT FOUND: No user with email {email} or name Lucas Echavarria on this DB.")

if __name__ == "__main__":
    force_reset()
