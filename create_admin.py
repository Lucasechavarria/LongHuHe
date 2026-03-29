import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model

User = get_user_model()

def create_user(username, email, password):
    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(
            username=username, 
            email=email, 
            password=password, 
            nombre='Admin', 
            apellido='Sistema', 
            celular=f"00000{username[:10]}" # Celular ficticio unico
        )
        print(f"Superusuario {username} creado con éxito.")
    else:
        print(f"El superusuario {username} ya existe.")

# Crear los administradores solicitados
create_user('lucas_admin', 'echavarrialucas1986@gmail.com', 'Anfaso12@')
create_user('long_hu_he', 'asociacionlonghuhe@gmail.com', 'asociacion')
