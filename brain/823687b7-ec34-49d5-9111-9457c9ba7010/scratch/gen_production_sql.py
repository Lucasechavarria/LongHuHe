import subprocess
import os

def get_sql(app, migration):
    try:
        result = subprocess.run(
            ['python', 'manage.py', 'sqlmigrate', app, migration],
            capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        return f"-- Error in {app} {migration}: {e.stderr}"

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
    all_sql.append(f"-- ==========================================\n-- {app}.{num}\n-- ==========================================")
    all_sql.append(get_sql(app, num))

with open('production_sync.sql', 'w') as f:
    f.write("\n\n".join(all_sql))

print("SQL generado en production_sync.sql")
