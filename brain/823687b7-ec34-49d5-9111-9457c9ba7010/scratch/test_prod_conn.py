import os
import sys
import dj_database_url
import psycopg2

# Get DATABASE_URL from .env manually to avoid django overhead
env_path = '.env'
db_url = None
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            if line.startswith('DATABASE_URL='):
                db_url = line.split('=', 1)[1].strip()
                break

if not db_url:
    print("No DATABASE_URL found in .env (or it is commented out)")
    sys.exit(1)

try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute('SELECT version();')
    print(f"Conexión exitosa: {cur.fetchone()[0]}")
    cur.close()
    conn.close()
except Exception as e:
    print(f"Error de conexión: {e}")
