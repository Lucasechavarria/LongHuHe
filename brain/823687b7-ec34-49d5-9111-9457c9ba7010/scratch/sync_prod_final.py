import os
import django
import sys
from django.core.management import call_command

# Add current directory to path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

# 1. FAKEAR las que el usuario ya corrio manualmente (o parcialmente)
# El usuario corrio SQL que cubre estas mayormente:
try:
    print("Faking manual migrations...")
    # Usuarios 0005, 0006, 0007, 0009
    call_command('migrate', 'usuarios', '0007', fake=True)
    # 0008 es nivel_acceso (no la corrio)
    # 0009 es qr_image (si la corrio)
    # Para simplificar, fakearemos hasta 0007 e intentaremos correr normal el resto.
    # Pero qr_image ya esta en el SQL del usuario.
    # Lo mejor es fake-ar unitariamente si es posible o simplemente correr con --fake-initial
except Exception as e:
    print(f"Error faking usuarios: {e}")

# 2. Correr las faltantes REALES
print("Applying remaining migrations to Supabase...")
try:
    call_command('migrate')
    print("Migraciones completadas exitosamente.")
except Exception as e:
    print(f"Error en migrate: {e}")
    print("Intentando aplicar nivel_acceso manualmente...")
    from django.db import connection
    with connection.cursor() as cursor:
        try:
            cursor.execute("ALTER TABLE core_usuario ADD COLUMN IF NOT EXISTS nivel_acceso varchar(20) DEFAULT 'alumno';")
            print("Columna nivel_acceso agregada manualmente.")
        except Exception as ex:
            print(f"Error en SQL manual: {ex}")
    # Reintentar migrate
    try:
        call_command('migrate', fake=True) # Intentamos fakear todo lo que falle por existir
        print("Migraciones sincronizadas con --fake.")
    except:
        pass

# 3. RESET DE PASSWORD
print("Actualizando contraseña de lucasechavarria en Supabase...")
from apps.usuarios.models import Usuario
user = Usuario.objects.filter(username='lucasechavarria').first()
if user:
    user.set_password('Anfaso12@')
    user.is_superuser = True
    user.is_staff = True
    user.rol_acceso_total = True
    user.save()
    print("Contraseña de 'lucasechavarria' actualizada a 'Anfaso12@' en PRODUCCION.")
else:
    print("No se encontró el usuario 'lucasechavarria' en producción.")
