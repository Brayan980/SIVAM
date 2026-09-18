import sqlite3

# Crear tabla usuarios
conexion = sqlite3.connect('clinica.db')
conexion.execute('''
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        usuario TEXT UNIQUE,
        contraseña_hash TEXT,
        rol TEXT
    )
''')
conexion.commit()
conexion.close()

print("Tabla 'usuarios' creada exitosamente en clinica.db")
