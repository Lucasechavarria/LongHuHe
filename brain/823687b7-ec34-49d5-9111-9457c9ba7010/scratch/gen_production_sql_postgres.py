import os
import sys
import django

# Add current directory to path
sys.path.append(os.getcwd())

from django.conf import settings

# Mock settings for Postgres to get correct SQL syntax
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'postgres',
        'USER': 'postgres',
        'PASSWORD': '',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

if not settings.configured:
    settings.configure(
        INSTALLED_APPS=[
            'django.contrib.contenttypes',
            'django.contrib.auth',
            'apps.usuarios',
            'apps.academia',
            'apps.asistencia',
            'apps.ventas',
            'apps.biblioteca',
            'apps.examenes',
        ],
        DATABASES=DATABASES,
    )
    django.setup()

from django.core.management import call_command
import io

def get_postgres_sql(app, migration):
    out = io.StringIO()
    try:
        call_command('sqlmigrate', app, migration, stdout=out)
        return out.getvalue()
    except Exception as e:
        return f"-- Error in {app} {migration}: {str(e)}"

migrations_to_gen = [
    ('usuarios', '0005'),
    ('usuarios', '0006'),
    ('usuarios', '0007'),
    ('usuarios', '0008'),
    ('usuarios', '0009'),
    ('ventas', '0002'),
    ('ventas', '0003'),
    ('ventas', '0004'),
    ('ventas', '0005'),
    ('ventas', '0006'),
]

all_sql = []
for app, num in migrations_to_gen:
    all_sql.append(f"-- ==========================================\n-- {app}.{num} (POSTGRES VERSION)\n-- ==========================================")
    all_sql.append(get_postgres_sql(app, num))

with open('production_sync_postgres.sql', 'w') as f:
    f.write("\n\n".join(all_sql))

print("SQL (Postgres) generado en production_sync_postgres.sql")
