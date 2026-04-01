import psycopg2
import os
import socket
from dotenv import load_dotenv

# Forzamos la carga del .env en la ruta absoluta
env_path = r'c:\Users\User\Desktop\Tai-Chi App\.env'
load_dotenv(dotenv_path=env_path)

db_url = os.getenv("DATABASE_URL")

if not db_url:
    print(f"❌ Error: DATABASE_URL no se cargó correctamente desde {env_path}")
    exit(1)

print(f"Probando URL (host): {db_url.split('@')[1] if '@' in db_url else 'No URL'}")

# 1. Prueba de DNS
host = "db.pzikczglcocxhosdpinw.supabase.co"
try:
    ip = socket.gethostbyname(host)
    print(f"🔍 DNS OK: {host} -> {ip}")
except Exception as e:
    print(f"❌ Error de DNS: {e}")

# 2. Prueba de Conexión DB
try:
    conn = psycopg2.connect(db_url)
    print("✅ Conexión exitosa a Supabase!")
    conn.close()
except Exception as e:
    print(f"❌ Error de conexión DB: {e}")
