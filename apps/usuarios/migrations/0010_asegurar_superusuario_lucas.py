from django.db import migrations

def asegurar_superusuario(apps, schema_editor):
    # Usamos apps.get_model para evitar problemas de importacion circular
    Usuario = apps.get_model('usuarios', 'Usuario')
    
    username = '1131078008'
    email = 'echavarrialucas1986@gmail.com'
    password = 'Anfaso12@'
    
    from django.contrib.auth.hashers import make_password
    
    user, created = Usuario.objects.get_or_create(username=username)
    
    user.email = email
    user.celular = username
    user.password = make_password(password)
    
    # Permisos base de Django
    user.is_superuser = True
    user.is_staff = True
    user.is_active = True
    
    # Roles especificos del ERP Long Hu He
    user.rol_acceso_total = True
    user.rol_gestion_alumnos = True
    user.rol_gestion_sedes = True
    user.rol_gestion_tienda = True
    user.rol_gestion_tesoreria = True
    user.rol_gestion_academia = True
    
    user.save()
    
    if created:
        print(f"\nUsuario Superadministrador '{username}' creado exitosamente.")
    else:
        print(f"\nUsuario Superadministrador '{username}' actualizado exitosamente.")

class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0009_usuario_qr_image_alter_usuario_qr_base64_cache'),
    ]

    operations = [
        migrations.RunPython(asegurar_superusuario),
    ]
