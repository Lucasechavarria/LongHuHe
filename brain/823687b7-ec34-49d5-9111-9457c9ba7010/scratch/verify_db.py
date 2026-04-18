import os
import django
import sys

# Add current directory to path
sys.path.append(os.getcwd())

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

try:
    django.setup()
    from django.db import connection
    with connection.cursor() as cursor:
        cursor.execute("SELECT version();")
        row = cursor.fetchone()
        print(f"Conexión exitosa a la base de datos: {row[0]}")
except Exception as e:
    print(f"Error de conexión: {e}")
