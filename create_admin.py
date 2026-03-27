import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.models import User

def create_user(username, email, password):
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username, email, password)
        print(f"Superusuario {username} creado con éxito.")
    else:
        print(f"El superusuario {username} ya existe.")

# Crear los administradores solicitados
create_user('lucas_admin', 'echavarrialucas1986@gmail.com', 'Anfaso12@')
create_user('long_hu_he', 'asociacionlonghuhe@gmail.com', 'asociacion')
