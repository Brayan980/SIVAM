import psycopg2
from dotenv import load_dotenv
import os

# Cargar variables de entorno
load_dotenv()
DATABASE_URL = os.getenv('DATABASE_URL')

# Conectar a PostgreSQL
conn = psycopg2.connect(DATABASE_URL)
cursor = conn.cursor()

print("CONTEOS POR TABLA EN POSTGRESQL")
print("=" * 40)

tablas = [
    'pacientes',
    'usuarios',
    'antropometria',
    'vo2_max',
    'test_moca',
    'test_tinetti',
    'test_chair_stand',
    'caracterizacion_socioeconomica'
]

for tabla in tablas:
    cursor.execute(f"SELECT COUNT(*) FROM {tabla}")
    count = cursor.fetchone()[0]
    print(f"{tabla:35} {count:5}")

print("=" * 40)

# Verificar pacientes únicos por tabla
print("\nPACIENTES ÚNICOS POR TABLA (COUNT DISTINCT paciente_id)")
print("=" * 60)

tablas_con_paciente = [
    'antropometria',
    'vo2_max',
    'test_moca',
    'test_tinetti',
    'test_chair_stand',
    'caracterizacion_socioeconomica'
]

for tabla in tablas_con_paciente:
    cursor.execute(f"SELECT COUNT(DISTINCT paciente_id) FROM {tabla}")
    count = cursor.fetchone()[0]
    print(f"{tabla:35} {count:5}")

conn.close()
