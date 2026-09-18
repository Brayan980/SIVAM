# ============================================================
# Migración de la tabla usuarios:
#  - Agrega columnas nombre_completo y fecha_creacion si faltan.
#  - Crea un usuario admin por defecto si no existe ninguno con rol 'admin'.
# Ejecutar una sola vez:  python migrar_usuarios.py
# ============================================================
import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash

DB = 'clinica.db'

conn = sqlite3.connect(DB)
cur = conn.cursor()

# 1) Columnas existentes
cur.execute("PRAGMA table_info(usuarios)")
cols = [c[1] for c in cur.fetchall()]

if 'nombre_completo' not in cols:
    cur.execute("ALTER TABLE usuarios ADD COLUMN nombre_completo TEXT")
    print("+ Columna 'nombre_completo' agregada.")

if 'fecha_creacion' not in cols:
    cur.execute("ALTER TABLE usuarios ADD COLUMN fecha_creacion TIMESTAMP")
    print("+ Columna 'fecha_creacion' agregada.")

# 2) Asegurar que exista al menos un admin
cur.execute("SELECT COUNT(*) FROM usuarios WHERE rol = 'admin'")
n_admin = cur.fetchone()[0]

if n_admin == 0:
    usuario = 'admin'
    password = 'admin123'  # el admin debe cambiarla luego
    # Evitar choque si ya existe un usuario 'admin' con otro rol
    cur.execute("SELECT id FROM usuarios WHERE usuario = ?", (usuario,))
    existente = cur.fetchone()
    if existente:
        cur.execute(
            "UPDATE usuarios SET rol = 'admin', contraseña_hash = ?, fecha_creacion = ? WHERE id = ?",
            (generate_password_hash(password), datetime.now().isoformat(), existente[0])
        )
        print(f"* Usuario '{usuario}' actualizado a rol admin.")
    else:
        cur.execute(
            "INSERT INTO usuarios (usuario, contraseña_hash, rol, nombre_completo, fecha_creacion) "
            "VALUES (?, ?, 'admin', ?, ?)",
            (usuario, generate_password_hash(password), 'Administrador', datetime.now().isoformat())
        )
        print(f"+ Usuario admin creado -> usuario: {usuario} / contraseña: {password}")
        print("  IMPORTANTE: cambia esta contraseña después de iniciar sesión.")
else:
    print(f"= Ya existen {n_admin} usuario(s) admin. No se creó ninguno.")

conn.commit()
conn.close()
print("Migración completada.")
