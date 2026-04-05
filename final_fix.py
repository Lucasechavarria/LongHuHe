import os
import django
from dotenv import load_dotenv

load_dotenv()
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['FORCE_REMOTE_DB'] = 'True'
django.setup()

from apps.usuarios.models import Usuario

def final_attempt():
    targets = [
        {'id': 7, 'username': 'lucasechavarria', 'celular': '1131078008', 'dni': '32764773'},
        {'id': 5, 'username': 'danielechavarria', 'celular': '1168774097', 'dni': '16197335'},
        {'id': 4, 'username': 'asociacion_lh', 'celular': '0000000000', 'dni': '1234567'} # DNI ficticio para evitar nulos
    ]
    
    for t in targets:
        try:
            u = Usuario.objects.get(id=t['id'])
            u.username = t['username']
            u.celular = t['celular']
            u.dni = t.get('dni', '')
            u.set_password('Lucas2026!')
            u.is_active = True
            u.is_staff = True
            u.is_superuser = True
            u.rol_acceso_total = True
            u.save()
            print(f"SUCCESS: {u.username} updated.")
        except Exception as e:
            print(f"ERROR: {t['username']} - {str(e)}")

if __name__ == "__main__":
    final_attempt()
