import os
import django

# Load .env
from dotenv import load_dotenv
load_dotenv()

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ['FORCE_REMOTE_DB'] = 'True'
django.setup()

from django.db import connection
print(f"Vendor: {connection.vendor}")
# For postgres, NAME is often it's actual DB name, but settings_dict has all of it.
db_name = connection.settings_dict.get('NAME', 'unknown')
db_host = connection.settings_dict.get('HOST', 'unknown')
print(f"Database NAME: {db_name}")
print(f"Database HOST: {db_host}")
