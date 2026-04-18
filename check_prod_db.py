import psycopg2
db_url = 'postgresql://postgres.pzikczglcocxhosdpinw:pjy6Bp%2ByW%3FkNn-e@aws-1-sa-east-1.pooler.supabase.com:6543/postgres'
try:
    conn = psycopg2.connect(db_url)
    cur = conn.cursor()
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'core_producto'")
    cols = [r[0] for r in cur.fetchall()]
    print('Columns in core_producto (PROD):', cols)
    
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = 'core_descuento'")
    cols_desc = [r[0] for r in cur.fetchall()]
    print('Columns in core_descuento (PROD):', cols_desc)

    cur.execute("SELECT name FROM django_migrations WHERE app = 'ventas' AND name LIKE '0004%'")
    mig = cur.fetchone()
    print('Migration 0004 status (PROD):', mig)
    
    cur.close()
    conn.close()
except Exception as e:
    print('Error:', e)
