# ============================================================
# SIVAM — Sistema de migraciones automáticas
#
# Al arrancar la app en producción, ejecuta los archivos .sql
# de scripts/migracion/ que aún no se han aplicado.
#
# Lleva un registro en la tabla `_migraciones` para no correr
# dos veces el mismo archivo.
# ============================================================
import os
import glob
import logging

logger = logging.getLogger(__name__)

DIRECTORIO_SQL = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              'scripts', 'migracion')


def _asegurar_tabla_migraciones(cursor):
    """Crea la tabla de control si no existe."""
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS _migraciones (
            nombre TEXT PRIMARY KEY,
            aplicada_en TIMESTAMPTZ DEFAULT NOW()
        )
    """)


def _migraciones_aplicadas(cursor):
    cursor.execute("SELECT nombre FROM _migraciones")
    return {fila[0] for fila in cursor.fetchall()}


def correr_migraciones(conexion):
    """Ejecuta todos los .sql de scripts/migracion/ que aún no se han aplicado.

    Recibe una conexión psycopg2 ya abierta (solo se usa en producción,
    con PostgreSQL/Supabase). En SQLite local no hace falta porque las
    migraciones usan IF NOT EXISTS y el schema local se gestiona por separado.
    """
    cursor = conexion.cursor()

    _asegurar_tabla_migraciones(cursor)
    conexion.commit()

    aplicadas = _migraciones_aplicadas(cursor)

    # Busca archivos .sql ordenados por nombre (que empieza con fecha YYYYMMDD)
    archivos = sorted(glob.glob(os.path.join(DIRECTORIO_SQL, '*.sql')))

    pendientes = [a for a in archivos if os.path.basename(a) not in aplicadas]

    if not pendientes:
        logger.info('Migraciones: nada pendiente.')
        return

    for ruta in pendientes:
        nombre = os.path.basename(ruta)
        logger.info(f'Migraciones: aplicando {nombre} ...')
        try:
            with open(ruta, encoding='utf-8') as f:
                sql = f.read()
            cursor.execute(sql)
            cursor.execute(
                "INSERT INTO _migraciones (nombre) VALUES (%s)", (nombre,)
            )
            conexion.commit()
            logger.info(f'Migraciones: {nombre} aplicada OK.')
        except Exception as e:
            conexion.rollback()
            logger.error(f'Migraciones: ERROR en {nombre}: {e}')
            raise

    cursor.close()
