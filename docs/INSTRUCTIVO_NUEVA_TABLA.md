# Instructivo: crear una nueva tabla en la base de datos

Guía paso a paso para agregar una tabla nueva al proyecto SIVAM. El sistema usa
**dos motores de base de datos**:

- **Local (desarrollo):** SQLite, archivo `data/clinica.db`. Se activa cuando NO
  existe la variable de entorno `DATABASE_URL`.
- **Producción (Render/Supabase):** PostgreSQL. Se activa cuando SÍ existe `DATABASE_URL`.

El código de acceso a datos (`db.py`) traduce automáticamente la sintaxis estilo
Postgres (`%s`, `RETURNING id`) a SQLite en local, así que **escribes el SQL una sola
vez con estilo Postgres** y funciona en ambos entornos.

> ⚠️ Regla de oro: la tabla debe crearse en **los dos entornos**. Si solo la creas en
> local, en producción dará "Internal Server Error" al usarla, y viceversa.

---

## Convenciones del proyecto (síguelas para mantener consistencia)

Mira cualquier tabla existente en `scripts/setup/crear_nuevas_tablas.py` como plantilla.
Toda tabla de módulo clínico sigue este patrón:

- `id SERIAL PRIMARY KEY` — identificador autoincremental.
- `paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE` —
  vincula el registro con un paciente y lo borra en cascada si el paciente se elimina.
- Las columnas propias del módulo (numéricas, texto, etc.).
- `resultado TEXT` — clasificación cualitativa, si aplica.
- `evaluador TEXT` y `observaciones TEXT` — opcionales pero habituales.
- `fecha_examen DATE` (en Postgres) / `TEXT` (en SQLite).
- `fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP` — cuándo se guardó.
- `creado_por INTEGER REFERENCES usuarios(id)` — qué usuario lo registró.

**Nombres de columnas:** minúsculas, sin tildes ni espacios, usa guion bajo
(`snake_case`). Evita la `ñ` (la única columna con `ñ` es `contraseña_hash` y obliga a
citarla con comillas dobles en Postgres, lo cual complica el código).

---

## Paso 1 — Definir el SQL de la tabla

Escribe el `CREATE TABLE` con estilo Postgres. Ejemplo de una tabla ficticia `test_fuerza`:

```
CREATE TABLE IF NOT EXISTS test_fuerza (
    id SERIAL PRIMARY KEY,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
    mano_derecha NUMERIC(5,2),
    mano_izquierda NUMERIC(5,2),
    resultado TEXT,
    evaluador TEXT,
    observaciones TEXT,
    fecha_examen DATE,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    creado_por INTEGER REFERENCES usuarios(id)
)
```

Tipos más usados en el proyecto:

| Dato | Postgres | SQLite (equivalente) |
|------|----------|----------------------|
| Entero | `INTEGER` | `INTEGER` |
| Decimal | `NUMERIC(5,2)` | `REAL` |
| Texto | `TEXT` | `TEXT` |
| Fecha | `DATE` | `TEXT` |
| Fecha y hora | `TIMESTAMP` | `TIMESTAMP` |
| Sí/No | `BOOLEAN` | `INTEGER` (0/1) |

Para restringir valores permitidos usa `CHECK`, como en las tablas existentes:
```
escolaridad TEXT CHECK (escolaridad IN ('Bachiller', 'Técnico', 'Universitarios', 'Ninguno'))
```

---

## Paso 2 — Crear la tabla en PRODUCCIÓN (PostgreSQL / Supabase)

Tienes dos opciones:

### Opción A — Agregar el SQL al script de setup (recomendado)

1. Abre `scripts/setup/crear_nuevas_tablas.py`.
2. Copia uno de los bloques `cursor.execute(sql.SQL(""" ... """))` existentes y adáptalo
   con tu nuevo `CREATE TABLE`.
3. Asegúrate de tener la variable `DATABASE_URL` de Supabase en el archivo `.env`.
4. Ejecútalo desde la raíz del proyecto:
   ```
   .venv\Scripts\python.exe scripts\setup\crear_nuevas_tablas.py
   ```
   Es seguro correrlo varias veces: usa `CREATE TABLE IF NOT EXISTS`, así que no
   duplica ni borra tablas existentes.

### Opción B — Ejecutar el SQL directo en el panel de Supabase

1. Entra a Supabase → SQL Editor.
2. Pega el `CREATE TABLE ...` del Paso 1.
3. Ejecuta.

---

## Paso 3 — Crear la tabla en LOCAL (SQLite)

Si trabajas también en local, crea la misma tabla en `data/clinica.db`. La forma más
simple es un script corto que use la capa `conectar()` del proyecto (ya elige SQLite
cuando no hay `DATABASE_URL`):

```
# scripts/setup/crear_tabla_fuerza.py
from db import conectar

conn = conectar()
cur = conn.cursor()
cur.execute('''
    CREATE TABLE IF NOT EXISTS test_fuerza (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE CASCADE,
        mano_derecha REAL,
        mano_izquierda REAL,
        resultado TEXT,
        evaluador TEXT,
        observaciones TEXT,
        fecha_examen TEXT,
        fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        creado_por INTEGER REFERENCES usuarios(id)
    )
''')
conn.commit()
conn.close()
print('Tabla test_fuerza creada en SQLite')
```
Ejecuta desde la raíz:
```
.venv\Scripts\python.exe scripts\setup\crear_tabla_fuerza.py
```

> Nota: en SQLite el autoincremental se escribe `INTEGER PRIMARY KEY AUTOINCREMENT`
> (no `SERIAL`). El resto del SQL es compatible.

---

## Paso 4 — Registrar la tabla en la migración maestra (importante)

Para que futuras migraciones completas SQLite → Supabase incluyan tu tabla, edita
`scripts/migracion/migrar_sqlite_a_supabase.py`:

1. Agrega el nombre de la tabla a la lista `TABLAS` (respetando el orden: primero las
   que no dependen de otras; tu tabla va después de `pacientes` y `usuarios` porque las
   referencia).
2. Agrega su `CREATE TABLE IF NOT EXISTS ...` dentro de la constante `DDL`.

Así el proyecto queda coherente y reproducible si algún día hay que rearmar la base.

---

## Paso 5 — Conectar la tabla con la aplicación (si es un módulo visible)

Si la tabla es solo de apoyo, con los pasos anteriores basta. Si va a ser un **módulo
clínico** que el usuario ve y llena, además hay que tocar `app.py` y las plantillas.
Usa un módulo existente (ej. `vo2_max`) como referencia y replica el patrón:

- **`app.py`** → función `registrar_modulo()` (aprox. línea 1122): agrega tu módulo al
  diccionario `modulos_validos` para que el botón redirija a su formulario.
- **`app.py`** → función `paciente_ficha()` (aprox. línea 543): agrega tu tabla a la
  lista de módulos que se leen para mostrarlos en la ficha del paciente.
- **`app.py`** → crea la ruta que muestra y guarda el formulario del módulo (`GET` para
  mostrar, `POST` para insertar/actualizar). Copia la estructura de una ruta de test
  existente (MoCA, Tinetti, etc.).
- **`templates/`** → crea el HTML del formulario (basado en uno existente como
  `templates/antropometria.html`).
- **`templates/index_sivam.html`** → si quieres que aparezca en "Módulos disponibles",
  agrégalo a la lista `modulos_disponibles`.
- **`campos.py`** → si el módulo tiene campos nuevos, añade sus etiquetas amigables al
  diccionario de etiquetas para que no se muestre el nombre técnico.

---

## Paso 6 — Verificar

1. **Local:** arranca la app y entra al módulo; crea y consulta un registro.
2. **Producción:** tras desplegar, repite la prueba. Si aparece "Internal Server Error",
   casi siempre es porque la tabla o una columna no existe en Postgres (repite el Paso 2)
   o hay un desajuste de tipo (ej. una fecha `TIMESTAMP` tratada como texto).

---

## Checklist rápido

- [ ] SQL `CREATE TABLE` escrito con estilo Postgres y convenciones del proyecto.
- [ ] Tabla creada en Supabase/PostgreSQL (Paso 2).
- [ ] Tabla creada en SQLite local (Paso 3).
- [ ] Tabla agregada a `TABLAS` y `DDL` en la migración maestra (Paso 4).
- [ ] (Si es módulo) rutas, plantillas y `campos.py` actualizados (Paso 5).
- [ ] Probado en local y en producción (Paso 6).

---

## Archivos clave de referencia

| Archivo | Para qué sirve |
|---------|----------------|
| `db.py` | Capa de conexión; elige SQLite o Postgres automáticamente. |
| `scripts/setup/crear_nuevas_tablas.py` | Plantilla de creación de tablas en Postgres. |
| `scripts/migracion/migrar_sqlite_a_supabase.py` | Esquema maestro (`DDL`) y lista `TABLAS`. |
| `app.py` | Rutas, registro de módulos y lectura de la ficha del paciente. |
| `campos.py` | Etiquetas amigables de los campos. |
| `templates/` | Formularios y vistas HTML. |
