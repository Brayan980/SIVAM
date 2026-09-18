import sqlite3
from werkzeug.security import generate_password_hash

# Crear usuario de prueba
usuario = "medico"
contraseña = "test123"
rol = "medico"

contraseña_hash = generate_password_hash(contraseña)

conexion = sqlite3.connect('clinica.db')
try:
    conexion.execute(
        'INSERT INTO usuarios (usuario, contraseña_hash, rol) VALUES (?, ?, ?)',
        (usuario, contraseña_hash, rol)
    )
    conexion.commit()
    print(f"Usuario '{usuario}' creado exitosamente con rol '{rol}'.")
    print(f"Contraseña: {contraseña}")
except sqlite3.IntegrityError:
    print(f"Error: El usuario '{usuario}' ya existe.")
finally:
    conexion.close()
