# SIVAM - CECAR

Sistema de vista médica: buscador y registro de historias clínicas con módulos
de evaluación (Antropometría, VO2 Max, MoCA, Tinetti, Chair Stand y
Caracterización socioeconómica), dashboards e informes en Excel.

Aplicación web en **Flask** con base de datos **SQLite**.

## Estructura del proyecto

```
vista_medico/
├── app.py                 # Aplicación Flask (rutas y lógica de vistas)
├── db.py                  # Capa de acceso a datos (SQLite, ruta a data/clinica.db)
├── campos.py              # Definición de campos clínicos y normalización
├── exportar.py            # Generación de reportes Excel (general e individual)
├── graficas.py            # Gráficas de los reportes + clasificaciones clínicas
│                          #   (VO2 Max y Chair Stand: única fuente de verdad)
├── templates/             # Plantillas Jinja2 (HTML)
├── static/                # CSS, JS e imágenes
│
├── data/                  # Datos (NO se versionan)
│   ├── clinica.db         # Base de datos activa
│   ├── backups/           # Copias de seguridad de la BD
│   └── *.xlsx / *.csv     # Fuentes de datos originales
│
├── scripts/               # Scripts auxiliares de un solo uso
│   ├── analisis/          # Exploración/diagnóstico de datos
│   ├── importacion/       # Importación desde Excel
│   ├── migracion/         # Migraciones y normalización de datos
│   └── setup/             # Creación de tablas y usuarios
│
├── docs/                  # Documentación del proyecto
├── requirements.txt       # Dependencias de Python
└── .env                   # Variables de entorno (NO se versiona)
```

## Puesta en marcha (desarrollo)

1. Crear y activar el entorno virtual:

   ```
   python -m venv .venv
   .venv\Scripts\activate      # Windows
   ```

2. Instalar dependencias:

   ```
   pip install -r requirements.txt
   ```

3. Configurar variables de entorno en un archivo `.env` en la raíz:

   ```
   SECRET_KEY=una-clave-larga-y-aleatoria
   ```

4. Ejecutar en desarrollo:

   ```
   python app.py
   ```

## Notas

- La base de datos vive en `data/clinica.db`. La ruta está resuelta de forma
  absoluta en `db.py`, así que la app funciona sin importar el directorio
  desde el que se arranque.
- Los scripts en `scripts/` son utilidades de un solo uso (importación inicial,
  migraciones ya aplicadas, diagnóstico). Si necesitas volver a ejecutar alguno,
  hazlo desde la raíz del proyecto (por ejemplo `python scripts\setup\crear_usuario.py`)
  y revisa las rutas relativas a datos que puedan contener.
- Antes de aplicar migraciones o normalizaciones sobre la BD, haz un backup en
  `data/backups/`.

## Despliegue en producción

- **No** usar el servidor de desarrollo de Flask. Usar un servidor WSGI:
  - Linux: `gunicorn -w 3 -b 127.0.0.1:8000 app:app`
  - Windows: `waitress-serve --port=8000 app:app`
- Servir detrás de Nginx/IIS con HTTPS.
- Definir `SECRET_KEY` como variable de entorno (no usar el valor por defecto).
- Desactivar el modo debug.
- Asegurar que `data/` esté en almacenamiento persistente y con backups.
