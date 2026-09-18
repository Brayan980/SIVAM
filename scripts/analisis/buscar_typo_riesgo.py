import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cursor = conn.cursor()

cursor.execute("SELECT id, riesgo_cardiovascular_con_riesgo_o_sin_riesgo FROM pacientes WHERE riesgo_cardiovascular_con_riesgo_o_sin_riesgo LIKE '%Rlesgo%'")
print("Pacientes con typo 'Rlesgo':")
for row in cursor.fetchall():
    print(f"ID: {row[0]}, Valor: {row[1]}")

conn.close()
