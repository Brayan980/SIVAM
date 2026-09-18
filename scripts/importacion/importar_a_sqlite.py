# ============================================================
# IMPORTAR CSV LIMPIO A SQLITE
# Crea clinica.db si no existe, y agrega solo los pacientes del
# CSV que todavia no esten en la tabla. Es seguro volver a correrlo:
# nunca borra ni duplica pacientes (incluyendo los que un medico
# haya agregado a mano desde la app).
# ============================================================

import pandas as pd
import sqlite3
from campos import CAMPOS, normalizar

# Paso 1: Crear la tabla si todavia no existe (con id autoincremental real,
# para que la app pueda insertar pacientes nuevos igual que este script)
conexion = sqlite3.connect('clinica.db')
columnas_sql = ',\n    '.join(f'{c} TEXT' for c in CAMPOS)
conexion.execute(f'''
    CREATE TABLE IF NOT EXISTS pacientes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        {columnas_sql},
        busqueda TEXT
    )
''')
conexion.execute('CREATE INDEX IF NOT EXISTS idx_busqueda ON pacientes (busqueda)')

# Paso 2: Leer el CSV ya limpio
df = pd.read_csv('historias_clinicas_limpias.csv')
df['busqueda'] = (df['nombres'].fillna('') + ' ' + df['apellidos'].fillna('')).apply(normalizar)

# Paso 3: Ver que pacientes ya existen en la base (por nombre normalizado)
existentes = {
    fila[0] for fila in conexion.execute('SELECT busqueda FROM pacientes')
}

# Paso 4: Insertar solo los pacientes del CSV que todavia no esten
placeholders = ', '.join('?' for _ in CAMPOS)
columnas_insert = ', '.join(CAMPOS)
nuevos = 0
for _, fila in df.iterrows():
    if fila['busqueda'] in existentes:
        continue
    valores = [fila.get(c) for c in CAMPOS] + [fila['busqueda']]
    conexion.execute(
        f'INSERT INTO pacientes ({columnas_insert}, busqueda) VALUES ({placeholders}, ?)',
        valores
    )
    existentes.add(fila['busqueda'])
    nuevos += 1

conexion.commit()
total = conexion.execute('SELECT COUNT(*) FROM pacientes').fetchone()[0]
conexion.close()

print(f"Pacientes nuevos importados: {nuevos}")
print(f"Total de pacientes en clinica.db: {total}")
