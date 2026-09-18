import sqlite3
from werkzeug.security import generate_password_hash
import getpass

# Pedir datos del usuario
usuario = input("Usuario: ").strip()
contraseña = getpass.getpass("Contraseña: ").strip()
rol = "medico"  # Por ahora solo un rol

if not usuario or not contraseña:
    print("Usuario y contraseña son obligatorios.")
    exit(1)

# Hashear la contraseña
contraseña_hash = generate_password_hash(contraseña)

# Insertar en la base de datos
conexion = sqlite3.connect('clinica.db')
try:
    conexion.execute(
        'INSERT INTO usuarios (usuario, contraseña_hash, rol) VALUES (?, ?, ?)',
        (usuario, contraseña_hash, rol)
    )
    conexion.commit()
    print(f"Usuario '{usuario}' creado exitosamente con rol '{rol}'.")
except sqlite3.IntegrityError:
    print(f"Error: El usuario '{usuario}' ya existe.")
finally:
    conexion.close()
