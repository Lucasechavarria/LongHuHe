import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from core.models import Usuario

def crear_o_actualizar_usuario(username, email, password, nombre, apellido, celular, is_superuser=False, es_profe=False, rol_total=False):
    # Buscamos por email para ser más precisos en la actualización
    user = Usuario.objects.filter(email=email).first()
    if not user:
        user = Usuario(username=username, email=email)
        print(f"Creando nuevo usuario: {username}")
    else:
        print(f"Actualizando usuario existente: {username}")
        
    user.set_password(password)
    user.nombre = nombre
    user.apellido = apellido
    user.celular = celular
    user.es_profe = es_profe
    user.rol_acceso_total = rol_total
    # El método save() del modelo se encargará de is_staff e is_superuser si rol_acceso_total es True
    user.save()
    print(f"Usuario {username} ({email}) procesado correctamente.")

# 1. Lucas Echavarria (Superuser)
crear_o_actualizar_usuario(
    username="lucasechavarria",
    email="echavarrialucas1986@gmail.com",
    password="Anfaso12@",
    nombre="Lucas",
    apellido="Echavarria",
    celular="1122334455",
    rol_total=True
)

# 2. Asociacion (Superuser)
crear_o_actualizar_usuario(
    username="asociacion",
    email="asociacionlonghuhe@gmail.com",
    password="LongHuHe",
    nombre="Asociacion",
    apellido="LongHuHe",
    celular="0000000000",
    rol_total=True
)

# 3. Daniel Echavarria (Maestro Principal)
crear_o_actualizar_usuario(
    username="danielechavarria",
    email="danielernestoechavarria7@gmail.com",
    password="longhuhe",
    nombre="Daniel",
    apellido="Echavarria",
    celular="3344556677",
    es_profe=True,
    rol_total=True
)
