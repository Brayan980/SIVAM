# ============================================================
# VISTA DEL MEDICO - Buscador y registro de historias clinicas
# ============================================================
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, abort
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from dotenv import load_dotenv
import os
import sqlite3
from datetime import datetime, timezone, date
from campos import CAMPOS, CAMPOS_CLINICOS, ETIQUETAS, normalizar, calcular_edad
from db import conectar
import exportar
import graficas

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'clave-secreta-para-sesiones')

# Versionar el texto permite demostrar qué información se presentó al titular.
VERSION_POLITICA_DATOS = 'SIVAM-PTD-1.0-2026-11-12'
TEXTO_AUTORIZACION_DATOS = (
    'Confirmo que he informado al paciente sobre las finalidades del tratamiento de '
    'sus datos personales y sensibles, sus derechos y la Política de Tratamiento de '
    'Datos Personales de SIVAM, y que he obtenido su autorización previa, expresa e '
    'informada para dicho tratamiento.'
)

ESTADOS_AUTORIZACION = {
    'autorizada',
    'sin_autorizacion_comprobable',
    'rechazada',
    'revocada',
}

TIPOS_DOCUMENTO = ('CC', 'TI', 'CE', 'Pasaporte')

# Se conservan como evidencia interna, pero no son datos clínicos que deban
# aparecer en la ficha principal ni en el modal del paciente.
CAMPOS_AUDITORIA_PRIVACIDAD = {
    'autoriza_tratamiento_datos', 'fecha_autorizacion', 'version_politica',
    'texto_autorizacion_aceptado', 'estado_autorizacion',
}
CAMPOS_AUDITORIA_INACTIVACION = {
    'activo', 'fecha_inactivacion', 'inactivado_por', 'inactivado_por_nombre',
    'fecha_reactivacion', 'reactivado_por', 'reactivado_por_nombre',
}


def _fecha_autorizacion_servidor():
    """Marca de tiempo UTC generada por el servidor, no por el navegador."""
    return datetime.now(timezone.utc)


def _estado_autorizacion(paciente):
    """Obtiene el estado actual sin reinterpretar ni reescribir datos históricos."""
    estado = paciente.get('estado_autorizacion')
    if estado in ESTADOS_AUTORIZACION:
        return estado
    if paciente.get('autoriza_tratamiento_datos'):
        return 'autorizada'
    return 'sin_autorizacion_comprobable'


def _paciente_esta_activo(paciente):
    """Los registros previos a la migración se tratan como activos."""
    return paciente.get('activo') not in (False, 0, '0', 'false', 'False')


def _paciente_activo_en_bd(cursor, paciente_id):
    """Comprueba que el paciente exista y siga disponible para operación clínica."""
    cursor.execute('SELECT activo FROM pacientes WHERE id = %s', (paciente_id,))
    fila = cursor.fetchone()
    return bool(fila) and fila[0] not in (False, 0, '0', 'false', 'False')


def _actualizar_edad_calculada(paciente, fecha_referencia=None):
    """Calcula solo para la vista; nunca reescribe edades ni historiales."""
    edad = calcular_edad(paciente.get('fecha_de_nacimiento'), fecha_referencia)
    if edad is not None:
        paciente['edad'] = edad
        paciente['edad_es_estimada'] = False
    return paciente


def _edad_para_evaluacion(paciente, fecha_examen=None):
    """Edad de la fecha de la prueba, sin alterar la historia del paciente."""
    try:
        referencia = date.fromisoformat(fecha_examen) if fecha_examen else date.today()
    except ValueError:
        referencia = date.today()
    edad = calcular_edad(paciente.get('fecha_de_nacimiento'), referencia)
    return edad if edad is not None else paciente.get('edad')

# Configuración de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'


@app.route('/health')
def health():
    """Endpoint ligero para monitoreo (UptimeRobot, cron-job, etc.).

    No requiere login ni consulta la base de datos, así que responde de
    inmediato. Sirve para hacer 'ping' periódico y evitar que Render
    duerma el servicio (cold start) en el plan gratuito.
    """
    return 'ok', 200


@app.route('/health')
def health():
    """Endpoint ligero para monitoreo (UptimeRobot, cron-job, etc.).

    No requiere login ni consulta la base de datos, así que responde de
    inmediato. Sirve para hacer 'ping' periódico y evitar que Render
    duerma el servicio (cold start) en el plan gratuito.
    """
    return 'ok', 200


class User(UserMixin):
    def __init__(self, user_id, usuario, rol):
        self.id = user_id
        self.usuario = usuario
        self.rol = rol


@login_manager.user_loader
def load_user(user_id):
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute('SELECT * FROM usuarios WHERE id = %s', (user_id,))
    fila = cursor.fetchone()
    conexion.close()
    if fila:
        return User(fila[0], fila[1], fila[3])
    return None


# Clasificaciones automáticas cuya tabla y lógica viven en graficas.py como
# única fuente de verdad, para que el resultado calculado y las bandas de la
# gráfica del reporte coincidan siempre.
#  - VO2 Max: Superior/Excelente/Bueno/Regular/Bajo
#  - Chair Stand: Muy Pobre/Pobre/Regular/Promedio/Alto/Superior (por edad y sexo)
from graficas import clasificar_vo2_max, clasificar_chair_stand


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usuario = request.form.get('usuario', '').strip()
        contraseña = request.form.get('contraseña', '').strip()

        if not usuario or not contraseña:
            flash('Usuario y contraseña son obligatorios.')
            return render_template('login.html')

        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute('SELECT * FROM usuarios WHERE usuario = %s', (usuario,))
        fila = cursor.fetchone()
        conexion.close()

        if fila and check_password_hash(fila[2], contraseña):
            user = User(fila[0], fila[1], fila[3])
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Usuario o contraseña incorrectos.')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


def admin_required(f):
    """Permite el acceso solo a usuarios con rol 'admin'."""
    @wraps(f)
    @login_required
    def wrapper(*args, **kwargs):
        if getattr(current_user, 'rol', None) != 'admin':
            abort(403)
        return f(*args, **kwargs)
    return wrapper


@app.errorhandler(403)
def acceso_denegado(e):
    """Página amigable cuando un usuario sin permisos intenta acceder."""
    return render_template('error_403.html'), 403


# ============================================================
# GESTIÓN DE USUARIOS (solo admin)
# ============================================================
ROLES_VALIDOS = ['admin', 'medico']


@app.route('/usuarios')
@admin_required
def usuarios_lista():
    """Lista todos los usuarios del sistema."""
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute(
        'SELECT id, usuario, rol, nombre_completo, fecha_creacion FROM usuarios ORDER BY usuario'
    )
    filas = cursor.fetchall()
    columnas = [desc[0] for desc in cursor.description]
    conexion.close()
    usuarios = [dict(zip(columnas, f)) for f in filas]
    # Normalizar fecha_creacion a texto: en PostgreSQL viene como datetime
    # y en SQLite como string ISO. El template espera poder cortar los
    # primeros 10 caracteres (YYYY-MM-DD).
    for u in usuarios:
        fecha = u.get('fecha_creacion')
        if fecha is not None and not isinstance(fecha, str):
            u['fecha_creacion'] = fecha.isoformat()
    # Normalizar fecha_creacion a texto: en PostgreSQL viene como datetime
    # y en SQLite como string ISO. El template espera poder cortar los
    # primeros 10 caracteres (YYYY-MM-DD).
    for u in usuarios:
        fecha = u.get('fecha_creacion')
        if fecha is not None and not isinstance(fecha, str):
            u['fecha_creacion'] = fecha.isoformat()
    return render_template('usuarios.html', usuarios=usuarios, roles=ROLES_VALIDOS)


@app.route('/usuarios/crear', methods=['POST'])
@admin_required
def usuarios_crear():
    """Crea un nuevo usuario."""
    usuario = request.form.get('usuario', '').strip()
    contrasena = request.form.get('contrasena', '').strip()
    rol = request.form.get('rol', '').strip()
    nombre_completo = request.form.get('nombre_completo', '').strip() or None

    if not usuario or not contrasena or rol not in ROLES_VALIDOS:
        flash('Usuario, contraseña y un rol válido son obligatorios.', 'error')
        return redirect(url_for('usuarios_lista'))

    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute('SELECT id FROM usuarios WHERE usuario = %s', (usuario,))
    if cursor.fetchone():
        conexion.close()
        flash(f'Ya existe un usuario llamado "{usuario}".', 'error')
        return redirect(url_for('usuarios_lista'))

    from datetime import datetime
    cursor.execute(
        '''INSERT INTO usuarios (usuario, contraseña_hash, rol, nombre_completo, fecha_creacion)
           VALUES (%s, %s, %s, %s, %s)''',
        (usuario, generate_password_hash(contrasena), rol, nombre_completo, datetime.now().isoformat())
    )
    conexion.commit()
    conexion.close()
    flash(f'Usuario "{usuario}" creado correctamente.', 'ok')
    return redirect(url_for('usuarios_lista'))


@app.route('/usuarios/<int:user_id>/editar', methods=['POST'])
@admin_required
def usuarios_editar(user_id):
    """Edita rol, nombre y (opcionalmente) contraseña de un usuario."""
    rol = request.form.get('rol', '').strip()
    nombre_completo = request.form.get('nombre_completo', '').strip() or None
    nueva_contrasena = request.form.get('contrasena', '').strip()

    if rol not in ROLES_VALIDOS:
        flash('Rol no válido.', 'error')
        return redirect(url_for('usuarios_lista'))

    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute('SELECT rol FROM usuarios WHERE id = %s', (user_id,))
    fila = cursor.fetchone()
    if not fila:
        conexion.close()
        flash('El usuario no existe.', 'error')
        return redirect(url_for('usuarios_lista'))

    # Evitar quedarse sin ningún admin: si este era admin y se le quita, verificar
    if fila[0] == 'admin' and rol != 'admin':
        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE rol = 'admin'")
        if cursor.fetchone()[0] <= 1:
            conexion.close()
            flash('No puedes quitar el rol admin al único administrador.', 'error')
            return redirect(url_for('usuarios_lista'))

    if nueva_contrasena:
        cursor.execute(
            'UPDATE usuarios SET rol = %s, nombre_completo = %s, contraseña_hash = %s WHERE id = %s',
            (rol, nombre_completo, generate_password_hash(nueva_contrasena), user_id)
        )
    else:
        cursor.execute(
            'UPDATE usuarios SET rol = %s, nombre_completo = %s WHERE id = %s',
            (rol, nombre_completo, user_id)
        )
    conexion.commit()
    conexion.close()
    flash('Usuario actualizado correctamente.', 'ok')
    return redirect(url_for('usuarios_lista'))


@app.route('/usuarios/<int:user_id>/eliminar', methods=['POST'])
@admin_required
def usuarios_eliminar(user_id):
    """Elimina un usuario, evitando borrar al propio admin logueado o al último admin."""
    if str(user_id) == str(current_user.id):
        flash('No puedes eliminar tu propia cuenta.', 'error')
        return redirect(url_for('usuarios_lista'))

    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute('SELECT rol FROM usuarios WHERE id = %s', (user_id,))
    fila = cursor.fetchone()
    if not fila:
        conexion.close()
        flash('El usuario no existe.', 'error')
        return redirect(url_for('usuarios_lista'))

    if fila[0] == 'admin':
        cursor.execute("SELECT COUNT(*) FROM usuarios WHERE rol = 'admin'")
        if cursor.fetchone()[0] <= 1:
            conexion.close()
            flash('No puedes eliminar al único administrador.', 'error')
            return redirect(url_for('usuarios_lista'))

    cursor.execute('DELETE FROM usuarios WHERE id = %s', (user_id,))
    conexion.commit()
    conexion.close()
    flash('Usuario eliminado.', 'ok')
    return redirect(url_for('usuarios_lista'))


@app.route('/pacientes')
@login_required
def pacientes():
    """Alias limpio para la lista de pacientes, sin heredar parámetros."""
    return redirect(url_for('index'))


@app.route('/pacientes')
@login_required
def pacientes():
    """Alias limpio para la lista de pacientes, sin heredar parámetros."""
    return redirect(url_for('index'))


@app.route('/')
@login_required
def index():
    query = request.args.get('q', '').strip()
    paciente_id = request.args.get('id', type=int)
    estado = request.args.get('estado', 'activos')
    if estado not in ('activos', 'inactivos', 'todos'):
        estado = 'activos'
    filtro_estado = {
        'activos': 'COALESCE(p.activo, TRUE) = TRUE',
        'inactivos': 'COALESCE(p.activo, TRUE) = FALSE',
        'todos': 'TRUE',
    }[estado]

    resultados = []
    paciente = None

    conexion = conectar()
    cursor = conexion.cursor()

    if paciente_id:
        cursor.execute(
            '''SELECT p.*, COALESCE(NULLIF(u.nombre_completo, ''), u.usuario) AS inactivado_por_nombre,
                      COALESCE(NULLIF(ur.nombre_completo, ''), ur.usuario) AS reactivado_por_nombre
               FROM pacientes p
               LEFT JOIN usuarios u ON u.id = p.inactivado_por
               LEFT JOIN usuarios ur ON ur.id = p.reactivado_por
               WHERE p.id = %s''',
            (paciente_id,)
        )
        fila = cursor.fetchone()
        if fila:
            columnas = [desc[0] for desc in cursor.description]
            paciente = dict(zip(columnas, fila))
            _actualizar_edad_calculada(paciente)
            paciente['esta_inactivo'] = not _paciente_esta_activo(paciente)
            cursor.execute(
                'SELECT 1 FROM consentimientos_tratamiento_datos WHERE paciente_id = %s LIMIT 1',
                (paciente_id,)
            )
            paciente['eliminacion_bloqueada'] = cursor.fetchone() is not None

            # Cargar datos de otros módulos si existen
            cursor.execute('SELECT * FROM antropometria WHERE paciente_id = %s', (paciente_id,))
            antropometria = cursor.fetchone()
            if antropometria:
                columnas_antro = [desc[0] for desc in cursor.description]
                paciente['antropometria'] = dict(zip(columnas_antro, antropometria))

            cursor.execute('SELECT * FROM vo2_max WHERE paciente_id = %s', (paciente_id,))
            vo2_max = cursor.fetchone()
            if vo2_max:
                columnas_vo2 = [desc[0] for desc in cursor.description]
                paciente['vo2_max'] = dict(zip(columnas_vo2, vo2_max))

            cursor.execute('SELECT * FROM test_moca WHERE paciente_id = %s', (paciente_id,))
            test_moca = cursor.fetchone()
            if test_moca:
                columnas_moca = [desc[0] for desc in cursor.description]
                paciente['test_moca'] = dict(zip(columnas_moca, test_moca))

            cursor.execute('SELECT * FROM test_tinetti WHERE paciente_id = %s', (paciente_id,))
            test_tinetti = cursor.fetchone()
            if test_tinetti:
                columnas_tinetti = [desc[0] for desc in cursor.description]
                paciente['test_tinetti'] = dict(zip(columnas_tinetti, test_tinetti))

            cursor.execute('SELECT * FROM test_chair_stand WHERE paciente_id = %s', (paciente_id,))
            test_chair_stand = cursor.fetchone()
            if test_chair_stand:
                columnas_chair = [desc[0] for desc in cursor.description]
                paciente['test_chair_stand'] = dict(zip(columnas_chair, test_chair_stand))

            cursor.execute('SELECT * FROM caracterizacion_socioeconomica WHERE paciente_id = %s', (paciente_id,))
            caracterizacion = cursor.fetchone()
            if caracterizacion:
                columnas_caract = [desc[0] for desc in cursor.description]
                paciente['caracterizacion'] = dict(zip(columnas_caract, caracterizacion))

    pagina = request.args.get('pagina', 1, type=int)
    if pagina < 1:
        pagina = 1
    por_pagina = 10
    total_paginas = 1

    if not paciente_id:
        if query:
            patron = f'%{normalizar(query)}%'
            cursor.execute(
                f'''SELECT COUNT(*) FROM pacientes p
                    WHERE p.busqueda LIKE %s AND {filtro_estado}''',
                (patron,)
            )
            total_filas = cursor.fetchone()[0]
            cursor.execute(
                f'''SELECT p.*, COALESCE(NULLIF(u.nombre_completo, ''), u.usuario) AS inactivado_por_nombre,
                           COALESCE(NULLIF(ur.nombre_completo, ''), ur.usuario) AS reactivado_por_nombre
                   FROM pacientes p
                   LEFT JOIN usuarios u ON u.id = p.inactivado_por
                   LEFT JOIN usuarios ur ON ur.id = p.reactivado_por
                   WHERE p.busqueda LIKE %s AND {filtro_estado}
                   ORDER BY p.apellidos, p.nombres
                   LIMIT %s OFFSET %s''',
                (patron, por_pagina, (pagina - 1) * por_pagina)
            )
        else:
            cursor.execute(f'SELECT COUNT(*) FROM pacientes p WHERE {filtro_estado}')
            total_filas = cursor.fetchone()[0]
            cursor.execute(
                f'''SELECT p.*, COALESCE(NULLIF(u.nombre_completo, ''), u.usuario) AS inactivado_por_nombre,
                           COALESCE(NULLIF(ur.nombre_completo, ''), ur.usuario) AS reactivado_por_nombre
                   FROM pacientes p
                   LEFT JOIN usuarios u ON u.id = p.inactivado_por
                   LEFT JOIN usuarios ur ON ur.id = p.reactivado_por
                   WHERE {filtro_estado}
                   ORDER BY p.apellidos, p.nombres
                   LIMIT %s OFFSET %s''',
                (por_pagina, (pagina - 1) * por_pagina)
            )
        filas = cursor.fetchall()
        columnas = [desc[0] for desc in cursor.description]
        resultados = [dict(zip(columnas, fila)) for fila in filas]
        for resultado in resultados:
            _actualizar_edad_calculada(resultado)
            resultado['esta_inactivo'] = not _paciente_esta_activo(resultado)
            cursor.execute(
                'SELECT 1 FROM consentimientos_tratamiento_datos WHERE paciente_id = %s LIMIT 1',
                (resultado['id'],)
            )
            resultado['eliminacion_bloqueada'] = cursor.fetchone() is not None
        total_paginas = max(1, -(-total_filas // por_pagina))

    conexion.close()

    detalle = None
    if paciente:
        detalle = [
            (ETIQUETAS.get(campo, campo), valor)
            for campo, valor in paciente.items()
            if campo not in ('id', 'nombres', 'apellidos', 'busqueda', 'tipo_documento', 'numero_documento', 'telefono')
            and campo not in CAMPOS_AUDITORIA_PRIVACIDAD
            and campo not in CAMPOS_AUDITORIA_INACTIVACION and valor not in (None, '')
            and campo not in ['antropometria', 'vo2_max', 'test_moca', 'test_tinetti', 'test_chair_stand', 'caracterizacion']
        ]
        detalle.extend([
            ('Tipo de documento', paciente.get('tipo_documento') or 'No registrado'),
            ('Número de documento', paciente.get('numero_documento') or 'No registrado'),
            ('Teléfono', paciente.get('telefono') or 'No registrado'),
        ])

    return render_template(
        'index_sivam.html',
        query=query,
        resultados=resultados,
        paciente=paciente,
        detalle=detalle,
        pagina=pagina,
        total_paginas=total_paginas,
        total_registros=(total_filas if not paciente_id else 0),
        estado=estado,
    )


@app.route('/paciente/<int:paciente_id>/dashboard')
@login_required
def dashboard_paciente(paciente_id):
    """Dashboard individual de un paciente: resumen de su información y de los
    resultados de cada test (con indicadores y gráficas de medidor)."""
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute(
        '''SELECT p.*, COALESCE(NULLIF(ui.nombre_completo, ''), ui.usuario) AS inactivado_por_nombre,
                  COALESCE(NULLIF(ur.nombre_completo, ''), ur.usuario) AS reactivado_por_nombre
           FROM pacientes p
           LEFT JOIN usuarios ui ON ui.id = p.inactivado_por
           LEFT JOIN usuarios ur ON ur.id = p.reactivado_por
           WHERE p.id = %s''',
        (paciente_id,)
    )
    fila = cursor.fetchone()
    if not fila:
        conexion.close()
        abort(404)
    columnas = [desc[0] for desc in cursor.description]
    paciente = dict(zip(columnas, fila))
    _actualizar_edad_calculada(paciente)

    def _cargar(tabla):
        cursor.execute(f'SELECT * FROM {tabla} WHERE paciente_id = %s', (paciente_id,))
        f = cursor.fetchone()
        if not f:
            return None
        cols = [d[0] for d in cursor.description]
        return dict(zip(cols, f))

    antro = _cargar('antropometria')
    vo2 = _cargar('vo2_max')
    moca = _cargar('test_moca')
    tinetti = _cargar('test_tinetti')
    chair = _cargar('test_chair_stand')
    caract = _cargar('caracterizacion_socioeconomica')
    conexion.close()

    sexo = paciente.get('sexo')
    edad = paciente.get('edad')

    def _f(valor):
        try:
            return float(valor) if valor not in (None, '') else None
        except (TypeError, ValueError):
            return None

    # ---- Tarjetas de indicadores tipo "medidor" (valor sobre un máximo) ----
    # Cada tarjeta: titulo, icono, valor mostrado, nivel/resultado, valor y
    # máximo para el gauge, y estado de color (bueno/medio/malo) para pintar.
    tarjetas = []

    # Antropometría: IMC
    if antro:
        imc = _f(antro.get('imc'))
        if imc is not None:
            if imc < 18.5:
                nivel_imc, estado = 'Bajo peso', 'medio'
            elif imc < 25:
                nivel_imc, estado = 'Normal', 'bueno'
            elif imc < 30:
                nivel_imc, estado = 'Sobrepeso', 'medio'
            else:
                nivel_imc, estado = 'Obesidad', 'malo'
            tarjetas.append({
                'titulo': 'IMC', 'icono': 'fa-ruler-vertical',
                'valor_txt': f'{imc:g}', 'nivel': nivel_imc,
                'gauge': imc, 'max': 40, 'estado': estado,
                'unidad': 'kg/m²',
            })
        # ICC (cintura/cadera)
        icc = exportar._calcular_icc(antro.get('circunferencia_cintura'),
                                     antro.get('circunferencia_cadera'))
        if icc is not None:
            riesgo_icc = exportar._clasificar_icc(icc, sexo)
            tarjetas.append({
                'titulo': 'Índice Cintura-Cadera', 'icono': 'fa-circle-notch',
                'valor_txt': f'{icc:g}', 'nivel': riesgo_icc,
                'gauge': icc, 'max': 1.2,
                'estado': 'malo' if riesgo_icc == 'Alto' else 'bueno',
                'unidad': '',
            })

    # VO2 Max
    if vo2:
        v = _f(vo2.get('vo2_max'))
        if v is not None:
            nivel = vo2.get('resultado') or graficas.clasificar_vo2_max(v, edad, sexo)
            estado = {'Superior': 'bueno', 'Excelente': 'bueno', 'Bueno': 'bueno',
                      'Regular': 'medio', 'Bajo': 'malo'}.get(nivel, 'medio')
            tarjetas.append({
                'titulo': 'VO2 Max', 'icono': 'fa-heartbeat',
                'valor_txt': f'{v:g}', 'nivel': nivel,
                'gauge': v, 'max': 60, 'estado': estado,
                'unidad': 'ml/kg/min',
            })

    # Test MoCA (0-30)
    if moca:
        pt = _f(moca.get('puntaje_total'))
        nivel = moca.get('resultado')
        estado = {'Normal': 'bueno', 'PDCL': 'medio', 'PDCM': 'malo',
                  'NADA MENTAL': 'malo'}.get(nivel, 'medio')
        tarjetas.append({
            'titulo': 'Test MoCA', 'icono': 'fa-brain',
            'valor_txt': (f'{pt:g}' if pt is not None else '—'), 'nivel': nivel or '—',
            'gauge': pt if pt is not None else 0, 'max': 30, 'estado': estado,
            'unidad': 'ptos',
        })

    # Test Tinetti (0-28)
    if tinetti:
        pt = _f(tinetti.get('puntaje_total'))
        nivel = tinetti.get('resultado')
        estado = {'Bajo Riesgo': 'bueno', 'Riesgo Moderado': 'medio',
                  'Alto Riesgo': 'malo'}.get(nivel, 'medio')
        tarjetas.append({
            'titulo': 'Test Tinetti', 'icono': 'fa-walking',
            'valor_txt': (f'{pt:g}' if pt is not None else '—'), 'nivel': nivel or '—',
            'gauge': pt if pt is not None else 0, 'max': 28, 'estado': estado,
            'unidad': 'ptos',
        })

    # Test Chair Stand (repeticiones)
    if chair:
        rep = _f(chair.get('repeticiones'))
        nivel = chair.get('resultado')
        estado = {'Superior': 'bueno', 'Alto': 'bueno', 'Promedio': 'bueno',
                  'Regular': 'medio', 'Pobre': 'malo', 'Muy Pobre': 'malo'}.get(nivel, 'medio')
        tarjetas.append({
            'titulo': 'Chair Stand', 'icono': 'fa-chair',
            'valor_txt': (f'{rep:g}' if rep is not None else '—'), 'nivel': nivel or '—',
            'gauge': rep if rep is not None else 0, 'max': 25, 'estado': estado,
            'unidad': 'reps',
        })

    # Recuento de evaluaciones realizadas
    realizados = sum(1 for m in (antro, vo2, moca, tinetti, chair, caract) if m)

    return render_template(
        'dashboard_paciente.html',
        paciente=paciente,
        antro=antro, vo2=vo2, moca=moca, tinetti=tinetti,
        chair=chair, caract=caract,
        tarjetas=tarjetas,
        realizados=realizados,
    )


@app.route('/historia_ficha/<int:paciente_id>')
@login_required
def historia_ficha(paciente_id):
    """Ficha de historia clínica para el modal, con secciones desplegables."""
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute('SELECT * FROM pacientes WHERE id = %s', (paciente_id,))
    fila = cursor.fetchone()
    if not fila:
        conexion.close()
        return '<p>Paciente no encontrado.</p>', 404
    columnas = [desc[0] for desc in cursor.description]
    p = dict(zip(columnas, fila))
    _actualizar_edad_calculada(p)
    conexion.close()
    return render_template('_historia_modal.html', p=p)


@app.route('/paciente_ficha/<int:paciente_id>')
@login_required
def paciente_ficha(paciente_id):
    """Devuelve el HTML de la ficha de un paciente para mostrar en un modal."""
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute(
        '''SELECT p.*, COALESCE(NULLIF(ui.nombre_completo, ''), ui.usuario) AS inactivado_por_nombre,
                  COALESCE(NULLIF(ur.nombre_completo, ''), ur.usuario) AS reactivado_por_nombre
           FROM pacientes p
           LEFT JOIN usuarios ui ON ui.id = p.inactivado_por
           LEFT JOIN usuarios ur ON ur.id = p.reactivado_por
           WHERE p.id = %s''',
        (paciente_id,)
    )
    fila = cursor.fetchone()
    if not fila:
        conexion.close()
        return '<p>Paciente no encontrado.</p>', 404

    columnas = [desc[0] for desc in cursor.description]
    paciente = dict(zip(columnas, fila))
    _actualizar_edad_calculada(paciente)
    paciente['esta_inactivo'] = not _paciente_esta_activo(paciente)

    # La ficha abierta desde el icono de ojo muestra el estado y, cuando
    # exista, la evidencia registrada de la autorización; no expone el texto
    # completo de la política ni datos que no son necesarios en esta vista.
    cursor.execute(
        '''SELECT c.fecha_autorizacion, c.version_politica,
                  COALESCE(NULLIF(u.nombre_completo, ''), u.usuario) AS registrado_por_nombre
           FROM consentimientos_tratamiento_datos c
           LEFT JOIN usuarios u ON u.id = c.registrado_por
           WHERE c.paciente_id = %s
           ORDER BY c.id DESC LIMIT 1''',
        (paciente_id,)
    )
    consentimiento_fila = cursor.fetchone()
    consentimiento = None
    if consentimiento_fila:
        columnas_consentimiento = [desc[0] for desc in cursor.description]
        consentimiento = dict(zip(columnas_consentimiento, consentimiento_fila))

    modulos = {}
    for tabla, clave in [('antropometria', 'antropometria'), ('vo2_max', 'vo2_max'),
                         ('test_moca', 'test_moca'), ('test_tinetti', 'test_tinetti'),
                         ('test_chair_stand', 'test_chair_stand'),
                         ('caracterizacion_socioeconomica', 'caracterizacion')]:
        cursor.execute(f'SELECT * FROM {tabla} WHERE paciente_id = %s', (paciente_id,))
        reg = cursor.fetchone()
        if reg:
            cols = [desc[0] for desc in cursor.description]
            modulos[clave] = dict(zip(cols, reg))

    conexion.close()

    detalle = [
        (ETIQUETAS.get(campo, campo), valor)
        for campo, valor in paciente.items()
        if campo not in ('id', 'nombres', 'apellidos', 'busqueda', 'tipo_documento', 'numero_documento', 'telefono')
        and campo not in CAMPOS_AUDITORIA_PRIVACIDAD
        and campo not in CAMPOS_AUDITORIA_INACTIVACION and valor not in (None, '')
    ]
    detalle.extend([
        ('Tipo de documento', paciente.get('tipo_documento') or 'No registrado'),
        ('Número de documento', paciente.get('numero_documento') or 'No registrado'),
        ('Teléfono', paciente.get('telefono') or 'No registrado'),
    ])

    return render_template(
        '_ficha_modal.html', paciente=paciente, detalle=detalle, modulos=modulos,
        estado_autorizacion=_estado_autorizacion(paciente), consentimiento=consentimiento,
    )


def _procesar_formulario(request_form, edad_es_estimada_original=None):
    """Valida y devuelve (errores, nombres, apellidos, valores_clinicos, busqueda)."""
    errores = []
    nombres = request_form.get('nombres', '').strip()
    apellidos = request_form.get('apellidos', '').strip()

    if not nombres or not apellidos:
        errores.append('Nombres y apellidos son obligatorios.')

    fecha_nacimiento = request_form.get('fecha_de_nacimiento', '').strip()
    desconoce_fecha = request_form.get('fecha_nacimiento_desconocida') == 'si'
    edad_manual = request_form.get('edad', '').strip()

    if fecha_nacimiento:
        edad_calculada = calcular_edad(fecha_nacimiento)
        if edad_calculada is None:
            errores.append('La fecha de nacimiento debe ser válida y no puede ser futura.')
            edad_es_estimada = edad_es_estimada_original
        else:
            edad_manual = str(edad_calculada)
            edad_es_estimada = False
    elif desconoce_fecha:
        try:
            edad_numerica = int(edad_manual)
            if not 0 <= edad_numerica <= 130:
                raise ValueError
        except (TypeError, ValueError):
            errores.append('La edad estimada debe ser un número entero entre 0 y 130.')
        edad_es_estimada = True
    else:
        # Mantiene la falta de certeza de registros históricos sin inferir un estado.
        edad_es_estimada = edad_es_estimada_original

    tipo_documento = request_form.get('tipo_documento', '').strip()
    numero_documento = request_form.get('numero_documento', '').strip()
    telefono = request_form.get('telefono', '').strip()
    if numero_documento and not tipo_documento:
        errores.append('Selecciona el tipo de documento cuando ingreses un número de documento.')
    if tipo_documento and tipo_documento not in TIPOS_DOCUMENTO:
        errores.append('El tipo de documento indicado no es válido.')
    if len(numero_documento) > 40:
        errores.append('El número de documento no puede superar 40 caracteres.')
    if len(telefono) > 40:
        errores.append('El teléfono no puede superar 40 caracteres.')

    valores_por_campo = {c: request_form.get(c, '').strip() for c in CAMPOS_CLINICOS}
    valores_por_campo['fecha_de_nacimiento'] = fecha_nacimiento
    valores_por_campo['edad'] = edad_manual
    valores_por_campo['tipo_documento'] = tipo_documento
    valores_por_campo['numero_documento'] = numero_documento
    valores_por_campo['telefono'] = telefono
    valores_clinicos = [valores_por_campo[c] for c in CAMPOS_CLINICOS]
    busqueda = normalizar(f'{nombres} {apellidos}')
    return errores, nombres, apellidos, valores_clinicos, busqueda, edad_es_estimada


def _registrar_autorizacion(cursor, paciente_id, fecha_autorizacion):
    """Conserva una evidencia que el trigger de BD no permite modificar."""
    cursor.execute(
        '''INSERT INTO consentimientos_tratamiento_datos
           (paciente_id, autoriza_tratamiento_datos, fecha_autorizacion,
            version_politica, texto_autorizacion_aceptado, registrado_por)
           VALUES (%s, %s, %s, %s, %s, %s)''',
        (paciente_id, True, fecha_autorizacion, VERSION_POLITICA_DATOS,
         TEXTO_AUTORIZACION_DATOS, getattr(current_user, 'id', None))
    )


@app.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo():
    errores = []

    if request.method == 'POST':
        errores, nombres, apellidos, valores_clinicos, busqueda, edad_es_estimada = _procesar_formulario(request.form)
        confirma_autorizacion = request.form.get('autoriza_tratamiento_datos') == 'si'
        estado_solicitado = request.form.get('estado_autorizacion') or ''
        if estado_solicitado not in ('', 'rechazada'):
            errores.append('El estado de autorización indicado no es válido.')
        if confirma_autorizacion and estado_solicitado == 'rechazada':
            errores.append('No puedes registrar una autorización y un rechazo al mismo tiempo.')

        if not errores:
            conexion = conectar()
            cursor = conexion.cursor()
            columnas_insert = ', '.join(CAMPOS)
            placeholders = ', '.join(['%s'] * len(CAMPOS))
            fecha_autorizacion = _fecha_autorizacion_servidor() if confirma_autorizacion else None
            estado_autorizacion = 'autorizada' if confirma_autorizacion else (estado_solicitado or None)
            cursor.execute(
                f'INSERT INTO pacientes ({columnas_insert}, busqueda, '
                'autoriza_tratamiento_datos, fecha_autorizacion, version_politica, '
                'texto_autorizacion_aceptado, estado_autorizacion) '
                f'VALUES ({placeholders}, %s, %s, %s, %s, %s, %s) RETURNING id',
                [nombres, apellidos] + valores_clinicos + [edad_es_estimada, busqueda, True if confirma_autorizacion else None,
                 fecha_autorizacion,
                 VERSION_POLITICA_DATOS if confirma_autorizacion else None,
                 TEXTO_AUTORIZACION_DATOS if confirma_autorizacion else None,
                 estado_autorizacion]
            )
            nuevo_id = cursor.fetchone()[0]
            if confirma_autorizacion:
                _registrar_autorizacion(cursor, nuevo_id, fecha_autorizacion)
            conexion.commit()
            conexion.close()

            return redirect(url_for('index', id=nuevo_id))

    return render_template(
        'formulario_paciente_sivam.html',
        campos_clinicos=CAMPOS_CLINICOS,
        etiquetas=ETIQUETAS,
        errores=errores,
        valores=request.form,
        modo='nuevo',
        paciente_id=None,
        tiene_autorizacion=False,
        texto_autorizacion=TEXTO_AUTORIZACION_DATOS,
        version_politica=VERSION_POLITICA_DATOS,
        today=date.today().isoformat(),
    )


@app.route('/editar/<int:paciente_id>', methods=['GET', 'POST'])
@login_required
def editar(paciente_id):
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute('SELECT * FROM pacientes WHERE id = %s', (paciente_id,))
    fila = cursor.fetchone()

    if not fila:
        conexion.close()
        return redirect(url_for('index'))

    columnas = [desc[0] for desc in cursor.description]
    valores = dict(zip(columnas, fila))
    _actualizar_edad_calculada(valores)
    if not _paciente_esta_activo(valores):
        conexion.close()
        flash('Este paciente está inactivo. Su información se conserva solo para consulta y no puede editarse.', 'error')
        return redirect(url_for('index', estado='inactivos'))
    valores_originales = valores.copy()
    estado_original = _estado_autorizacion(valores_originales)
    errores = []

    if request.method == 'POST':
        errores, nombres, apellidos, valores_clinicos, busqueda, edad_es_estimada = _procesar_formulario(
            request.form, valores_originales.get('edad_es_estimada')
        )
        valores = request.form
        confirma_autorizacion = request.form.get('autoriza_tratamiento_datos') == 'si'
        estado_solicitado = request.form.get('estado_autorizacion') or ''

        if estado_solicitado not in ('', 'rechazada', 'revocada'):
            errores.append('El estado de autorización indicado no es válido.')
        if confirma_autorizacion and estado_solicitado:
            errores.append('No puedes registrar una autorización y otro estado al mismo tiempo.')
        if estado_solicitado == 'revocada' and estado_original != 'autorizada':
            errores.append('Solo puede registrarse una revocatoria cuando existe una autorización vigente.')

        if not errores:
            asignaciones = ', '.join(f'{c} = %s' for c in CAMPOS)
            cursor.execute(
                f'UPDATE pacientes SET {asignaciones}, busqueda = %s WHERE id = %s',
                [nombres, apellidos] + valores_clinicos + [edad_es_estimada, busqueda, paciente_id]
            )
            # Un registro histórico continúa disponible sin presumir autorización.
            # La autorización solo se registra tras una acción explícita del profesional.
            if estado_original in ('sin_autorizacion_comprobable', 'rechazada') and confirma_autorizacion:
                fecha_autorizacion = _fecha_autorizacion_servidor()
                cursor.execute(
                    '''UPDATE pacientes
                       SET autoriza_tratamiento_datos = %s, fecha_autorizacion = %s,
                           version_politica = %s, texto_autorizacion_aceptado = %s,
                           estado_autorizacion = %s
                       WHERE id = %s''',
                    (True, fecha_autorizacion, VERSION_POLITICA_DATOS,
                     TEXTO_AUTORIZACION_DATOS, 'autorizada', paciente_id)
                )
                _registrar_autorizacion(cursor, paciente_id, fecha_autorizacion)
            elif estado_solicitado == 'rechazada' and estado_original == 'sin_autorizacion_comprobable':
                cursor.execute(
                    'UPDATE pacientes SET estado_autorizacion = %s WHERE id = %s',
                    ('rechazada', paciente_id)
                )
            elif estado_solicitado == 'revocada':
                # Se conserva la evidencia histórica de la autorización; el estado
                # vigente indica que fue revocada y no altera aquella evidencia.
                cursor.execute(
                    'UPDATE pacientes SET estado_autorizacion = %s WHERE id = %s',
                    ('revocada', paciente_id)
                )
            conexion.commit()
            conexion.close()
            # Volver al origen guardado en el form hidden, o al dashboard del paciente
            volver = request.form.get('volver_url') or url_for('dashboard_paciente', paciente_id=paciente_id)
            return redirect(volver)
            # Volver al origen guardado en el form hidden, o al dashboard del paciente
            volver = request.form.get('volver_url') or url_for('dashboard_paciente', paciente_id=paciente_id)
            return redirect(volver)

    conexion.close()

    # Determinar destino del botón Volver según origen
    origen = request.args.get('origen', '')
    if origen == 'lista':
        volver_url = url_for('historia_clinica')
    elif origen == 'pacientes':
        volver_url = url_for('index')
    else:
        volver_url = url_for('dashboard_paciente', paciente_id=paciente_id)

    # Determinar destino del botón Volver según origen
    origen = request.args.get('origen', '')
    if origen == 'lista':
        volver_url = url_for('historia_clinica')
    elif origen == 'pacientes':
        volver_url = url_for('index')
    else:
        volver_url = url_for('dashboard_paciente', paciente_id=paciente_id)

    return render_template(
        'formulario_paciente_sivam.html',
        campos_clinicos=CAMPOS_CLINICOS,
        etiquetas=ETIQUETAS,
        errores=errores,
        valores=valores,
        modo='editar',
        paciente_id=paciente_id,
        volver_url=volver_url,
        estado_autorizacion=estado_original,
        texto_autorizacion=TEXTO_AUTORIZACION_DATOS,
        version_politica=VERSION_POLITICA_DATOS,
        today=date.today().isoformat(),
    )


@app.route('/politica-tratamiento-datos')
def politica_tratamiento_datos():
    """Política pública, disponible antes de entregar la autorización."""
    return render_template(
        'politica_tratamiento_datos.html',
        version_politica=VERSION_POLITICA_DATOS,
        contacto_datos=os.getenv('CONTACTO_PROTECCION_DATOS') or 'pendiente de configuración institucional',
        telefono_datos=os.getenv('TELEFONO_PROTECCION_DATOS') or 'pendiente de configuración institucional',
        direccion_datos=os.getenv('DIRECCION_PROTECCION_DATOS') or 'pendiente de configuración institucional',
    )


@app.route('/eliminar/<int:paciente_id>', methods=['POST'])
@login_required
def eliminar(paciente_id):
    conexion = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute('SELECT activo FROM pacientes WHERE id = %s', (paciente_id,))
        fila = cursor.fetchone()
        if not fila:
            flash('Paciente no encontrado.', 'error')
            return redirect(url_for('index'))
        if fila[0] in (False, 0, '0', 'false', 'False'):
            flash('El paciente ya está inactivo; su información y trazabilidad se conservan.', 'error')
            return redirect(url_for('index', estado='inactivos'))
        cursor.execute(
            'SELECT 1 FROM consentimientos_tratamiento_datos WHERE paciente_id = %s LIMIT 1',
            (paciente_id,)
        )
        if cursor.fetchone():
            flash('No se puede eliminar el paciente porque conserva una autorización de tratamiento de datos registrada.', 'error')
            return redirect(url_for('index'))
        cursor.execute('DELETE FROM pacientes WHERE id = %s', (paciente_id,))
        conexion.commit()
        flash('Paciente eliminado correctamente.', 'ok')
    except sqlite3.OperationalError as error:
        if conexion:
            conexion.rollback()
        if 'database is locked' in str(error).lower():
            flash('No se pudo eliminar el paciente porque la base de datos está ocupada. Espera unos segundos e inténtalo nuevamente.', 'error')
        else:
            raise
    except sqlite3.IntegrityError:
        if conexion:
            conexion.rollback()
        flash('No se pudo eliminar el paciente porque conserva información protegida asociada.', 'error')
    finally:
        if conexion:
            conexion.close()
    return redirect(url_for('index'))


@app.route('/pacientes/<int:paciente_id>/inactivar', methods=['POST'])
@login_required
def inactivar_paciente(paciente_id):
    """Retira un paciente de la operación diaria sin borrar su historia ni evidencia."""
    conexion = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute('SELECT activo FROM pacientes WHERE id = %s', (paciente_id,))
        fila = cursor.fetchone()
        if not fila:
            flash('Paciente no encontrado.', 'error')
            return redirect(url_for('index'))
        if fila[0] in (False, 0, '0', 'false', 'False'):
            flash('El paciente ya estaba inactivo.', 'error')
            return redirect(url_for('index', estado='inactivos'))

        cursor.execute(
            'SELECT 1 FROM consentimientos_tratamiento_datos WHERE paciente_id = %s LIMIT 1',
            (paciente_id,)
        )
        if not cursor.fetchone():
            flash('Solo se inactivan pacientes con una autorización registrada. Este registro puede eliminarse si no tiene otras relaciones protegidas.', 'error')
            return redirect(url_for('index', id=paciente_id))

        cursor.execute(
            '''UPDATE pacientes
               SET activo = %s, fecha_inactivacion = %s, inactivado_por = %s
               WHERE id = %s''',
            (False, _fecha_autorizacion_servidor(), getattr(current_user, 'id', None), paciente_id)
        )
        conexion.commit()
        flash('Paciente inactivado. Su historia clínica y la evidencia de autorización se conservan.', 'ok')
        return redirect(url_for('index', estado='activos'))
    except sqlite3.OperationalError as error:
        if conexion:
            conexion.rollback()
        if 'database is locked' in str(error).lower():
            flash('No se pudo inactivar el paciente porque la base de datos está ocupada. Espera unos segundos e inténtalo nuevamente.', 'error')
        else:
            raise
    finally:
        if conexion:
            conexion.close()
    return redirect(url_for('index', id=paciente_id))


@app.route('/pacientes/<int:paciente_id>/reactivar', methods=['POST'])
@login_required
def reactivar_paciente(paciente_id):
    """Devuelve un paciente inactivo a la operación clínica y deja trazabilidad."""
    conexion = None
    try:
        conexion = conectar()
        cursor = conexion.cursor()
        cursor.execute('SELECT activo FROM pacientes WHERE id = %s', (paciente_id,))
        fila = cursor.fetchone()
        if not fila:
            flash('Paciente no encontrado.', 'error')
            return redirect(url_for('index'))
        if fila[0] not in (False, 0, '0', 'false', 'False'):
            flash('El paciente ya está activo.', 'error')
            return redirect(url_for('index', id=paciente_id))

        cursor.execute(
            '''UPDATE pacientes
               SET activo = %s, fecha_reactivacion = %s, reactivado_por = %s
               WHERE id = %s''',
            (True, _fecha_autorizacion_servidor(), getattr(current_user, 'id', None), paciente_id)
        )
        conexion.commit()
        flash('Paciente reactivado. Puede volver a seleccionarse para atención y evaluaciones.', 'ok')
        return redirect(url_for('index', estado='activos'))
    except sqlite3.OperationalError as error:
        if conexion:
            conexion.rollback()
        if 'database is locked' in str(error).lower():
            flash('No se pudo reactivar el paciente porque la base de datos está ocupada. Espera unos segundos e inténtalo nuevamente.', 'error')
        else:
            raise
    finally:
        if conexion:
            conexion.close()
    return redirect(url_for('index', estado='inactivos'))


# Rutas para selección de paciente y módulos
@app.route('/historia_clinica')
@login_required
def historia_clinica():
    """Listado de historias clínicas con tabla y paginación."""
    query = request.args.get('q', '').strip()
    pagina = request.args.get('pagina', 1, type=int)
    if pagina < 1:
        pagina = 1
    por_pagina = 10

    conexion = conectar()
    cursor = conexion.cursor()

    if query:
        patron = f'%{normalizar(query)}%'
        # Filtro amplio: nombre/apellido, patología, barrio y riesgo cardiovascular
        filtro = '''(busqueda LIKE %s
                     OR LOWER(patologia_actual) LIKE %s
                     OR LOWER(barrio) LIKE %s
                     OR LOWER(riesgo_cardiovascular_con_riesgo_o_sin_riesgo) LIKE %s)'''
        params_filtro = (patron, patron, patron, patron)
        cursor.execute(
            f'SELECT COUNT(*) FROM pacientes WHERE ({filtro}) AND COALESCE(activo, TRUE) = TRUE',
            params_filtro,
        )
        total_filas = cursor.fetchone()[0]
        cursor.execute(
            f'''SELECT id, nombres, apellidos, edad, fecha_creacion, patologia_actual,
                      ejercicio_y_actividad_fisica_leve_moderado_intenso,
                      riesgo_cardiovascular_con_riesgo_o_sin_riesgo
               FROM pacientes WHERE ({filtro}) AND COALESCE(activo, TRUE) = TRUE
               ORDER BY apellidos, nombres LIMIT %s OFFSET %s''',
            params_filtro + (por_pagina, (pagina - 1) * por_pagina)
        )
    else:
        cursor.execute('SELECT COUNT(*) FROM pacientes WHERE COALESCE(activo, TRUE) = TRUE')
        total_filas = cursor.fetchone()[0]
        cursor.execute(
            '''SELECT id, nombres, apellidos, edad, patologia_actual,
                      ejercicio_y_actividad_fisica_leve_moderado_intenso,
                      riesgo_cardiovascular_con_riesgo_o_sin_riesgo
               FROM pacientes WHERE COALESCE(activo, TRUE) = TRUE
               ORDER BY apellidos, nombres LIMIT %s OFFSET %s''',
            (por_pagina, (pagina - 1) * por_pagina)
        )

    filas = cursor.fetchall()
    columnas = [desc[0] for desc in cursor.description]
    resultados = [dict(zip(columnas, fila)) for fila in filas]
    conexion.close()

    total_paginas = max(1, -(-total_filas // por_pagina))

    return render_template(
        'historia_clinica_lista.html',
        resultados=resultados,
        query=query,
        pagina=pagina,
        total_paginas=total_paginas,
        total_registros=total_filas,
    )


@app.route('/exportar_datos')
@login_required
def exportar_datos():
    """Exporta TODA la base de datos a un Excel con una hoja por módulo."""
    buffer = exportar.generar_excel()
    return send_file(
        buffer,
        as_attachment=True,
        download_name=exportar.nombre_archivo(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


@app.route('/exportar_paciente/<int:paciente_id>')
@login_required
def exportar_paciente(paciente_id):
    """Exporta los datos de un solo paciente a Excel (una hoja por módulo)."""
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute('SELECT nombres, apellidos FROM pacientes WHERE id = %s', (paciente_id,))
    fila = cursor.fetchone()
    conexion.close()
    if not fila:
        return redirect(url_for('historia_clinica'))

    nombre_completo = f'{fila[0]} {fila[1]}'
    buffer = exportar.generar_excel_individual(paciente_id)
    if buffer is None:
        return redirect(url_for('historia_clinica'))
    return send_file(
        buffer,
        as_attachment=True,
        download_name=exportar.nombre_archivo(paciente_id, nombre_completo),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


@app.route('/reporte_pendientes')
@login_required
def reporte_pendientes():
    """Reporte de pacientes pendientes por examen, con tabla de detalle."""
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute('SELECT COUNT(*) FROM pacientes')
    total_pacientes = cursor.fetchone()[0]

    # Exámenes disponibles (clave -> tabla)
    tablas = {
        'antropometria': 'antropometria',
        'vo2_max': 'vo2_max',
        'test_moca': 'test_moca',
        'test_tinetti': 'test_tinetti',
        'test_chair_stand': 'test_chair_stand',
    }

    examenes_seleccionados = request.args.getlist('examenes')
    # Si el formulario fue enviado (aplicado=1) respetamos la selección aunque
    # esté vacía. Solo en la primera visita ponemos todos por defecto.
    if not examenes_seleccionados and not request.args.get('aplicado'):
        examenes_seleccionados = list(tablas.keys())

    query = request.args.get('q', '').strip()

    # Conjunto de paciente_id que tienen cada examen
    tiene = {}
    for ex in examenes_seleccionados:
        if ex in tablas:
            cursor.execute(f'SELECT DISTINCT paciente_id FROM {tablas[ex]}')
            tiene[ex] = {row[0] for row in cursor.fetchall()}

    # Traer todos los pacientes (con filtro opcional)
    if query:
        patron = f'%{normalizar(query)}%'
        cursor.execute(
            'SELECT id, nombres, apellidos, sexo FROM pacientes WHERE busqueda LIKE %s ORDER BY apellidos, nombres',
            (patron,)
        )
    else:
        cursor.execute('SELECT id, nombres, apellidos, sexo FROM pacientes ORDER BY apellidos, nombres')
    pacientes = cursor.fetchall()
    conexion.close()

    # Construir filas de la tabla: por paciente, OK/falta por examen
    filas = []
    completos = 0
    for pid, nom, ape, sexo in pacientes:
        estado = {}
        todos_ok = True
        for ex in examenes_seleccionados:
            ok = pid in tiene.get(ex, set())
            estado[ex] = ok
            if not ok:
                todos_ok = False
        if todos_ok and examenes_seleccionados:
            completos += 1
        filas.append({
            'id': pid, 'nombres': nom, 'apellidos': ape, 'sexo': sexo,
            'estado': estado,
        })

    pendientes = len(pacientes) - completos

    # Etiquetas legibles para las columnas
    etiquetas_ex = {
        'antropometria': 'Antropometría', 'vo2_max': 'VO2 Max',
        'test_moca': 'MoCA', 'test_tinetti': 'Tinetti', 'test_chair_stand': 'Chair Stand',
    }

    return render_template(
        'reporte_pendientes.html',
        total_pacientes=total_pacientes,
        completos=completos,
        pendientes=pendientes,
        examenes_seleccionados=examenes_seleccionados,
        filas=filas,
        etiquetas_ex=etiquetas_ex,
        query=query,
    )



@app.route('/configuracion')
@login_required
def configuracion():
    """Página de configuración del sistema."""
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute('SELECT COUNT(*) FROM pacientes')
    total_pacientes = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(DISTINCT paciente_id) FROM test_moca')
    total_moca = cursor.fetchone()[0]

    total_evaluaciones = 0
    for tabla in (
        'antropometria',
        'vo2_max',
        'test_moca',
        'test_tinetti',
        'test_chair_stand',
        'caracterizacion_socioeconomica'
    ):
        cursor.execute(f'SELECT COUNT(*) FROM {tabla}')
        total_evaluaciones += cursor.fetchone()[0]

    conexion.close()

    usuario = getattr(current_user, 'usuario', None)
    rol = getattr(current_user, 'rol', None)

    return render_template(
        'configuracion.html',
        version='1.0.0',
        total_pacientes=total_pacientes,
        total_moca=total_moca,
        total_evaluaciones=total_evaluaciones,
        tipo_base='PostgreSQL / Supabase' if os.getenv('DATABASE_URL') else 'SQLite (local)',
        usuario=usuario,
        rol=rol,
    )

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard con conteos reales de cada módulo"""
    conexion = conectar()
    cursor = conexion.cursor()

    # El total conserva la visión histórica; la operación diaria usa activos.
    cursor.execute('SELECT COUNT(*) FROM pacientes')
    total_pacientes = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM pacientes WHERE COALESCE(activo, TRUE) = TRUE')
    pacientes_activos = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM pacientes WHERE COALESCE(activo, TRUE) = FALSE')
    pacientes_inactivos = cursor.fetchone()[0]

    # Antropometría
    cursor.execute('SELECT COUNT(DISTINCT paciente_id) FROM antropometria')
    total_antropometria = cursor.fetchone()[0]

    # VO2 Max
    cursor.execute('SELECT COUNT(DISTINCT paciente_id) FROM vo2_max')
    total_vo2 = cursor.fetchone()[0]

    # Test Chair Stand
    cursor.execute('SELECT COUNT(DISTINCT paciente_id) FROM test_chair_stand')
    total_chair_stand = cursor.fetchone()[0]

    # Test Tinetti
    cursor.execute('SELECT COUNT(DISTINCT paciente_id) FROM test_tinetti')
    total_tinetti = cursor.fetchone()[0]

    # Test MoCA
    cursor.execute('SELECT COUNT(DISTINCT paciente_id) FROM test_moca')
    total_moca = cursor.fetchone()[0]

    # Caracterización socioeconómica
    cursor.execute('SELECT COUNT(DISTINCT paciente_id) FROM caracterizacion_socioeconomica')
    total_caracterizacion = cursor.fetchone()[0]

    def conteo_por(tabla, columna):
        """Devuelve lista de (categoria, cantidad) para una columna, ignorando nulos."""
        cursor.execute(
            f"SELECT {columna}, COUNT(*) FROM {tabla} "
            f"WHERE {columna} IS NOT NULL AND {columna} <> '' "
            f"GROUP BY {columna} ORDER BY COUNT(*) DESC"
        )
        return [{'label': r[0], 'valor': r[1]} for r in cursor.fetchall()]

    graf_chair = conteo_por('test_chair_stand', 'resultado')
    graf_tinetti = conteo_por('test_tinetti', 'resultado')
    graf_moca = conteo_por('test_moca', 'resultado')
    graf_vo2 = conteo_por('test_moca', 'resultado') if False else conteo_por('vo2_max', 'resultado')
    graf_riesgo_cv = conteo_por('antropometria', 'riesgo_cardiovascular')
    graf_caracterizacion = conteo_por('caracterizacion_socioeconomica', 'estado_socioeconomico')

    # IMC por categorías
    cursor.execute("SELECT COUNT(*) FROM antropometria WHERE imc < 18.5")
    imc_bajo = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM antropometria WHERE imc >= 18.5 AND imc < 25")
    imc_normal = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM antropometria WHERE imc >= 25 AND imc < 30")
    imc_sobre = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM antropometria WHERE imc >= 30")
    imc_obesidad = cursor.fetchone()[0]
    graf_imc = [
        {'label': 'Bajo peso', 'valor': imc_bajo},
        {'label': 'Normal', 'valor': imc_normal},
        {'label': 'Sobrepeso', 'valor': imc_sobre},
        {'label': 'Obesidad', 'valor': imc_obesidad},
    ]
    graf_imc = [g for g in graf_imc if g['valor'] > 0]

    conexion.close()

    return render_template(
        'dashboard.html',
        total_pacientes=total_pacientes,
        pacientes_activos=pacientes_activos,
        pacientes_inactivos=pacientes_inactivos,
        total_antropometria=total_antropometria,
        total_vo2=total_vo2,
        total_chair_stand=total_chair_stand,
        total_tinetti=total_tinetti,
        total_moca=total_moca,
        total_caracterizacion=total_caracterizacion,
        graf_chair=graf_chair,
        graf_tinetti=graf_tinetti,
        graf_moca=graf_moca,
        graf_vo2=graf_vo2,
        graf_riesgo_cv=graf_riesgo_cv,
        graf_imc=graf_imc,
        graf_caracterizacion=graf_caracterizacion,
    )
@app.route('/seleccionar_paciente', methods=['GET', 'POST'])
@login_required
def seleccionar_paciente():
    """Primero seleccionar paciente existente antes de crear módulos"""
    query = request.args.get('q', '').strip()
    # Leer el módulo destino tanto de la query (GET) como del form (POST)
    siguiente_modulo = request.args.get('modulo', '') or request.form.get('modulo', '')

    paciente_seleccionado = None

    if request.method == 'POST':
        paciente_id = request.form.get('paciente_id', type=int)
        if paciente_id:
            conexion = conectar()
            cursor = conexion.cursor()
            disponible = _paciente_activo_en_bd(cursor, paciente_id)
            conexion.close()
            if not disponible:
                flash('Este paciente está inactivo y no puede seleccionarse para registrar nuevas evaluaciones.', 'error')
                return redirect(url_for('seleccionar_paciente', modulo=siguiente_modulo, q=query or None))
            # Guardar paciente en sesión para usar en siguiente módulo
            from flask import session
            session['paciente_seleccionado_id'] = paciente_id

            if siguiente_modulo:
                # Se llegó desde la lista de selección: volver a esa lista
                session['volver_formulario_url'] = url_for(
                    'seleccionar_paciente', modulo=siguiente_modulo, q=query or None
                )
                return redirect(url_for(siguiente_modulo))
            else:
                return redirect(url_for('index'))

    elif query:
        # Búsqueda de pacientes
        conexion = conectar()
        cursor = conexion.cursor()
        patron = f'%{normalizar(query)}%'
        cursor.execute(
            '''SELECT id, nombres, apellidos FROM pacientes
               WHERE busqueda LIKE %s AND COALESCE(activo, TRUE) = TRUE
               ORDER BY apellidos, nombres LIMIT 20''',
            (patron,)
        )
        resultados = cursor.fetchall()
        conexion.close()
    else:
        resultados = []

    return render_template(
        'seleccionar_paciente.html',
        query=query,
        resultados=resultados,
        siguiente_modulo=siguiente_modulo,
        paciente_seleccionado=paciente_seleccionado
    )


# Rutas para módulos
@app.route('/antropometria', methods=['GET', 'POST'])
@login_required
def antropometria():
    """Vista tipo dashboard de Antropometría con tabla de pacientes"""
    conexion = conectar()
    cursor = conexion.cursor()

    # Obtener estadísticas
    cursor.execute('SELECT COUNT(DISTINCT paciente_id) FROM antropometria')
    total_mediciones = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM pacientes')
    total_pacientes = cursor.fetchone()[0]

    pendientes = total_pacientes - total_mediciones

    # Categorías de IMC
    cursor.execute('SELECT COUNT(*) FROM antropometria WHERE imc < 18.5')
    bajo_peso = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM antropometria WHERE imc >= 18.5 AND imc < 25')
    peso_normal = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM antropometria WHERE imc >= 25 AND imc < 30')
    sobrepeso = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM antropometria WHERE imc >= 30')
    obesidad = cursor.fetchone()[0]

    # Buscador y paginación
    query = request.args.get('q', '').strip()
    pagina = request.args.get('pagina', 1, type=int)
    if pagina < 1:
        pagina = 1
    por_pagina = 10

    columnas_select = '''p.id, p.nombres, p.apellidos, p.edad, a.sexo, a.talla, a.peso, a.imc,
                   a.porcentaje_grasa_corporal, a.circunferencia_cintura, a.circunferencia_cadera,
                   a.riesgo_cardiovascular, a.sarcopenia, a.fecha_examen'''

    if query:
        patron = f'%{normalizar(query)}%'
        cursor.execute('SELECT COUNT(*) FROM pacientes p WHERE p.busqueda LIKE %s', (patron,))
        total_filas = cursor.fetchone()[0]
        cursor.execute(f'''
            SELECT {columnas_select}
            FROM pacientes p
            LEFT JOIN antropometria a ON p.id = a.paciente_id
            WHERE p.busqueda LIKE %s
            ORDER BY p.apellidos, p.nombres
            LIMIT %s OFFSET %s
        ''', (patron, por_pagina, (pagina - 1) * por_pagina))
    else:
        total_filas = total_pacientes
        cursor.execute(f'''
            SELECT {columnas_select}
            FROM pacientes p
            LEFT JOIN antropometria a ON p.id = a.paciente_id
            ORDER BY p.apellidos, p.nombres
            LIMIT %s OFFSET %s
        ''', (por_pagina, (pagina - 1) * por_pagina))

    filas = cursor.fetchall()
    columnas = [desc[0] for desc in cursor.description]
    resultados = [dict(zip(columnas, fila)) for fila in filas]

    # Calcular ICC (cintura/cadera) y su clasificación al vuelo
    for r in resultados:
        cintura = r.get('circunferencia_cintura')
        cadera = r.get('circunferencia_cadera')
        if cintura and cadera and float(cadera) > 0:
            icc = round(float(cintura) / float(cadera), 2)
            r['icc'] = icc
            # Clasificación ICC según sexo (umbrales OMS)
            sexo = (r.get('sexo') or '').lower()
            # Hombre/Masculino: acepta 'h' (Hombre) y 'm' de Masculino (excluyendo 'mu' de Mujer)
            if sexo.startswith('h') or (sexo.startswith('m') and not sexo.startswith('mu')):  # Hombre/Masculino
                limite_alto = 0.90
            elif sexo.startswith('mu') or sexo.startswith('f'):  # Mujer/Femenino
                limite_alto = 0.85
            else:
                limite_alto = 0.85
            r['icc_resultado'] = 'Alto' if icc >= limite_alto else 'Normal'
        else:
            r['icc'] = None
            r['icc_resultado'] = None

    total_paginas = max(1, -(-total_filas // por_pagina))  # ceil

    conexion.close()

    return render_template(
        'antropometria_dashboard.html',
        total_mediciones=total_mediciones,
        total_pacientes=total_pacientes,
        pendientes=pendientes,
        bajo_peso=bajo_peso,
        peso_normal=peso_normal,
        sobrepeso=sobrepeso,
        obesidad=obesidad,
        query=query,
        resultados=resultados,
        pagina=pagina,
        total_paginas=total_paginas,
    )


@app.route('/registrar_modulo/<modulo>/<int:paciente_id>')
@login_required
def registrar_modulo(modulo, paciente_id):
    """Fija el paciente en sesión y redirige al formulario del módulo.

    El parámetro opcional ?origen= indica desde dónde se llegó:
      - 'dashboard' → volver al dashboard del paciente
      - 'lista' (o cualquier otro valor) → volver a la lista del módulo
    Por defecto, si no se indica, se vuelve a la lista del módulo.
    """
    """Fija el paciente en sesión y redirige al formulario del módulo.

    El parámetro opcional ?origen= indica desde dónde se llegó:
      - 'dashboard' → volver al dashboard del paciente
      - 'lista' (o cualquier otro valor) → volver a la lista del módulo
    Por defecto, si no se indica, se vuelve a la lista del módulo.
    """
    from flask import session
    modulos_validos = {
        'antropometria': 'antropometria_formulario',
        'vo2_max': 'vo2_max_formulario',
        'test_moca': 'test_moca_formulario',
        'test_tinetti': 'test_tinetti_formulario',
        'test_chair_stand': 'test_chair_stand_formulario',
        'caracterizacion': 'caracterizacion_socioeconomica',
    }
    # Rutas de lista por módulo (para volver a la lista correspondiente)
    listas_modulos = {
        'antropometria': 'antropometria',
        'vo2_max': 'vo2_max',
        'test_moca': 'test_moca',
        'test_tinetti': 'test_tinetti',
        'test_chair_stand': 'test_chair_stand',
        'caracterizacion': 'caracterizacion',
    }
    # Rutas de lista por módulo (para volver a la lista correspondiente)
    listas_modulos = {
        'antropometria': 'antropometria',
        'vo2_max': 'vo2_max',
        'test_moca': 'test_moca',
        'test_tinetti': 'test_tinetti',
        'test_chair_stand': 'test_chair_stand',
        'caracterizacion': 'caracterizacion',
    }
    destino = modulos_validos.get(modulo)
    if not destino:
        return redirect(url_for('index'))

    conexion = conectar()
    cursor = conexion.cursor()
    disponible = _paciente_activo_en_bd(cursor, paciente_id)
    conexion.close()
    if not disponible:
        flash('Este paciente está inactivo y no puede recibir nuevas evaluaciones.', 'error')
        return redirect(url_for('index', estado='inactivos'))

    origen = request.args.get('origen', 'lista')
    if origen == 'dashboard':
        volver = url_for('dashboard_paciente', paciente_id=paciente_id)
    elif origen == 'pacientes':
        volver = url_for('index')
    else:
        lista_route = listas_modulos.get(modulo)
        volver = url_for(lista_route) if lista_route else url_for('index')

    session['paciente_seleccionado_id'] = paciente_id
    session['volver_formulario_url'] = volver
    session['volver_formulario_url'] = volver
    return redirect(url_for(destino))


def _pendientes_de(tabla):
    """Devuelve los pacientes que NO tienen registro en la tabla dada."""
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute(f'''
        SELECT p.id, p.nombres, p.apellidos, p.sexo
        FROM pacientes p
        LEFT JOIN {tabla} t ON p.id = t.paciente_id
        WHERE t.id IS NULL AND COALESCE(p.activo, TRUE) = TRUE
        ORDER BY p.apellidos, p.nombres
    ''')
    filas = cursor.fetchall()
    columnas = [desc[0] for desc in cursor.description]
    pendientes = [dict(zip(columnas, f)) for f in filas]
    conexion.close()
    return pendientes


@app.route('/vo2_max_pendientes')
@login_required
def vo2_max_pendientes():
    return render_template('pendientes_modulo.html', titulo='VO2 Max',
        subtitulo='Pacientes sin prueba de VO2 Max', modulo='vo2_max',
        volver_url='/vo2_max', pendientes=_pendientes_de('vo2_max'))


@app.route('/test_moca_pendientes')
@login_required
def test_moca_pendientes():
    return render_template('pendientes_modulo.html', titulo='Test MoCA',
        subtitulo='Pacientes sin evaluación MoCA', modulo='test_moca',
        volver_url='/test_moca', pendientes=_pendientes_de('test_moca'))


@app.route('/test_tinetti_pendientes')
@login_required
def test_tinetti_pendientes():
    return render_template('pendientes_modulo.html', titulo='Test Tinetti',
        subtitulo='Pacientes sin evaluación Tinetti', modulo='test_tinetti',
        volver_url='/test_tinetti', pendientes=_pendientes_de('test_tinetti'))


@app.route('/test_chair_stand_pendientes')
@login_required
def test_chair_stand_pendientes():
    return render_template('pendientes_modulo.html', titulo='Test Chair Stand',
        subtitulo='Pacientes sin prueba de Chair Stand', modulo='test_chair_stand',
        volver_url='/test_chair_stand', pendientes=_pendientes_de('test_chair_stand'))


@app.route('/caracterizacion_pendientes')
@login_required
def caracterizacion_pendientes():
    return render_template('pendientes_modulo.html', titulo='Caracterización',
        subtitulo='Pacientes sin caracterización socioeconómica', modulo='caracterizacion',
        volver_url='/caracterizacion', pendientes=_pendientes_de('caracterizacion_socioeconomica'))


@app.route('/antropometria_pendientes')
@login_required
def antropometria_pendientes():
    """Lista de pacientes sin medición de antropometría, con botón Registrar."""
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute('''
        SELECT p.id, p.nombres, p.apellidos, p.sexo
        FROM pacientes p
        LEFT JOIN antropometria a ON p.id = a.paciente_id
        WHERE a.id IS NULL AND COALESCE(p.activo, TRUE) = TRUE
        ORDER BY p.apellidos, p.nombres
    ''')
    filas = cursor.fetchall()
    columnas = [desc[0] for desc in cursor.description]
    pendientes = [dict(zip(columnas, f)) for f in filas]
    conexion.close()

    return render_template(
        'pendientes_modulo.html',
        titulo='Antropometría',
        subtitulo='Pacientes sin mediciones antropométricas',
        modulo='antropometria',
        volver_url='/antropometria',
        pendientes=pendientes,
    )


@app.route('/antropometria_formulario', methods=['GET', 'POST'])
@login_required
def antropometria_formulario():
    """Formulario individual de antropometría"""
    from flask import session

    paciente_id = session.get('paciente_seleccionado_id')
    if not paciente_id:
        return redirect(url_for('seleccionar_paciente', modulo='antropometria_formulario'))

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute('SELECT * FROM pacientes WHERE id = %s AND COALESCE(activo, TRUE) = TRUE', (paciente_id,))
    paciente = cursor.fetchone()
    if not paciente:
        session.pop('paciente_seleccionado_id', None)
        return redirect(url_for('seleccionar_paciente', modulo='antropometria_formulario'))

    columnas = [desc[0] for desc in cursor.description]
    paciente_dict = dict(zip(columnas, paciente))
    _actualizar_edad_calculada(paciente_dict)

    cursor.execute('SELECT * FROM antropometria WHERE paciente_id = %s', (paciente_id,))
    antropometria_existente = cursor.fetchone()
    valores = {}
    if antropometria_existente:
        columnas_antro = [desc[0] for desc in cursor.description]
        valores = dict(zip(columnas_antro, antropometria_existente))

    if request.method == 'POST':
        campos = ['sexo', 'talla', 'peso', 'imc', 'porcentaje_grasa_corporal',
                 'musculo_esqueletico', 'porcentaje_grasa_visceral',
                 'circunferencia_cintura', 'circunferencia_cadera',
                 'circunferencia_cuadriceps', 'circunferencia_pantorrilla',
                 'circunferencia_brazo', 'fuerza_lado_derecho', 'fuerza_lado_izquierdo',
                 'anchura_brazo', 'anchura_muneca', 'anchura_rodilla',
                 'riesgo_cardiovascular', 'sarcopenia', 'fecha_examen']

        # Campos vacíos -> None para no romper columnas NUMERIC/DATE ni los CHECK
        valores_form = {campo: (request.form.get(campo) or None) for campo in campos}

        if antropometria_existente:
            asignaciones = ', '.join(f'{c} = %s' for c in campos if c != 'id')
            valores_update = [valores_form[c] for c in campos if c != 'id']
            cursor.execute(
                f'UPDATE antropometria SET {asignaciones} WHERE paciente_id = %s',
                valores_update + [paciente_id]
            )
        else:
            columnas_insert = ', '.join(campos)
            placeholders = ', '.join(['%s'] * len(campos))
            cursor.execute(
                f'INSERT INTO antropometria (paciente_id, {columnas_insert}) VALUES (%s, {placeholders})',
                [paciente_id] + [valores_form[c] for c in campos]
            )

        conexion.commit()
        conexion.close()
        volver = request.form.get('volver_url') or session.pop('volver_formulario_url', None) or url_for('antropometria')
        return redirect(volver)
        volver = request.form.get('volver_url') or session.pop('volver_formulario_url', None) or url_for('antropometria')
        return redirect(volver)

    conexion.close()

    volver_url = session.pop('volver_formulario_url', None) or url_for('antropometria')
    volver_url = session.pop('volver_formulario_url', None) or url_for('antropometria')

    return render_template(
        'antropometria.html',
        paciente=paciente_dict,
        valores=valores,
        existe=bool(antropometria_existente),
        volver_url=volver_url
    )


@app.route('/vo2_max', methods=['GET', 'POST'])
@login_required
def vo2_max():
    """Vista tipo dashboard de VO2 Max con tabla de pacientes"""
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute('SELECT COUNT(DISTINCT paciente_id) FROM vo2_max')
    total_tests = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM pacientes')
    total_pacientes = cursor.fetchone()[0]

    pendientes = total_pacientes - total_tests

    # Categorías de resultado VO2 (case-insensitive)
    def _cuenta_vo2(*variantes):
        marcadores = ', '.join(['%s'] * len(variantes))
        cursor.execute(
            f'SELECT COUNT(*) FROM vo2_max WHERE LOWER(resultado) IN ({marcadores})',
            tuple(v.lower() for v in variantes)
        )
        return cursor.fetchone()[0]

    superior = _cuenta_vo2('Superior')
    excelente = _cuenta_vo2('Excelente')
    bueno = _cuenta_vo2('Bueno')
    regular = _cuenta_vo2('Regular')
    bajo = _cuenta_vo2('Bajo')

    query = request.args.get('q', '').strip()
    pagina = request.args.get('pagina', 1, type=int)
    if pagina < 1:
        pagina = 1
    por_pagina = 10

    cols = '''p.id, p.nombres, p.apellidos, v.edad, v.ta, v.fc, v.fc_max, v.spo2,
                   v.vo2_max, v.resultado, v.observaciones'''

    if query:
        patron = f'%{normalizar(query)}%'
        cursor.execute('SELECT COUNT(*) FROM pacientes p WHERE p.busqueda LIKE %s', (patron,))
        total_filas = cursor.fetchone()[0]
        cursor.execute(f'''
            SELECT {cols}
            FROM pacientes p
            LEFT JOIN vo2_max v ON p.id = v.paciente_id
            WHERE p.busqueda LIKE %s
            ORDER BY p.apellidos, p.nombres
            LIMIT %s OFFSET %s
        ''', (patron, por_pagina, (pagina - 1) * por_pagina))
    else:
        total_filas = total_pacientes
        cursor.execute(f'''
            SELECT {cols}
            FROM pacientes p
            LEFT JOIN vo2_max v ON p.id = v.paciente_id
            ORDER BY p.apellidos, p.nombres
            LIMIT %s OFFSET %s
        ''', (por_pagina, (pagina - 1) * por_pagina))

    filas = cursor.fetchall()
    columnas = [desc[0] for desc in cursor.description]
    resultados = [dict(zip(columnas, fila)) for fila in filas]
    total_paginas = max(1, -(-total_filas // por_pagina))

    conexion.close()

    return render_template(
        'vo2_max_dashboard.html',
        total_tests=total_tests,
        total_pacientes=total_pacientes,
        pendientes=pendientes,
        superior=superior,
        excelente=excelente,
        bueno=bueno,
        regular=regular,
        bajo=bajo,
        query=query,
        resultados=resultados,
        pagina=pagina,
        total_paginas=total_paginas,
    )


@app.route('/vo2_max_formulario', methods=['GET', 'POST'])
@login_required
def vo2_max_formulario():
    """Formulario individual de VO2 Max"""
    from flask import session

    paciente_id = session.get('paciente_seleccionado_id')
    if not paciente_id:
        return redirect(url_for('seleccionar_paciente', modulo='vo2_max_formulario'))

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute('SELECT * FROM pacientes WHERE id = %s AND COALESCE(activo, TRUE) = TRUE', (paciente_id,))
    paciente = cursor.fetchone()
    if not paciente:
        session.pop('paciente_seleccionado_id', None)
        return redirect(url_for('seleccionar_paciente', modulo='vo2_max_formulario'))

    columnas = [desc[0] for desc in cursor.description]
    paciente_dict = dict(zip(columnas, paciente))
    _actualizar_edad_calculada(paciente_dict)

    cursor.execute('SELECT * FROM vo2_max WHERE paciente_id = %s', (paciente_id,))
    vo2_existente = cursor.fetchone()
    valores = {}
    if vo2_existente:
        columnas_vo2 = [desc[0] for desc in cursor.description]
        valores = dict(zip(columnas_vo2, vo2_existente))

    if request.method == 'POST':
        campos = ['edad', 'ta', 'fc', 'fc_max', 'spo2', 'vo2_max', 'resultado', 'observaciones', 'fecha_examen']
        # Campos vacíos -> None para no romper columnas NUMERIC/INTEGER/DATE
        valores_form = {campo: (request.form.get(campo) or None) for campo in campos}

        # El resultado cualitativo NO se ingresa manualmente: se calcula en el
        # backend con el VO2 Max, la edad y el sexo del paciente (escala Cooper/ACSM).
        valores_form['resultado'] = clasificar_vo2_max(
            valores_form.get('vo2_max'),
            valores_form.get('edad'),
            paciente_dict.get('sexo'),
        )

        if vo2_existente:
            asignaciones = ', '.join(f'{c} = %s' for c in campos if c != 'id')
            valores_update = [valores_form[c] for c in campos if c != 'id']
            cursor.execute(
                f'UPDATE vo2_max SET {asignaciones} WHERE paciente_id = %s',
                valores_update + [paciente_id]
            )
        else:
            columnas_insert = ', '.join(campos)
            placeholders = ', '.join(['%s'] * len(campos))
            cursor.execute(
                f'INSERT INTO vo2_max (paciente_id, {columnas_insert}) VALUES (%s, {placeholders})',
                [paciente_id] + [valores_form[c] for c in campos]
            )

        conexion.commit()
        conexion.close()
        volver = request.form.get('volver_url') or session.pop('volver_formulario_url', None) or url_for('vo2_max')
        return redirect(volver)
        volver = request.form.get('volver_url') or session.pop('volver_formulario_url', None) or url_for('vo2_max')
        return redirect(volver)

    conexion.close()

    volver_url = session.pop('volver_formulario_url', None) or url_for('vo2_max')
    volver_url = session.pop('volver_formulario_url', None) or url_for('vo2_max')

    return render_template('vo2_max.html', paciente=paciente_dict, valores=valores,
                           existe=bool(vo2_existente), volver_url=volver_url)


@app.route('/test_moca', methods=['GET', 'POST'])
@login_required
def test_moca():
    """Vista tipo dashboard de Test MoCA con tabla de pacientes"""
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute('SELECT COUNT(DISTINCT paciente_id) FROM test_moca')
    total_tests = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM pacientes')
    total_pacientes = cursor.fetchone()[0]

    pendientes = total_pacientes - total_tests

    # Categorías de resultado MoCA (case-insensitive)
    def _cuenta_moca(*variantes):
        marcadores = ', '.join(['%s'] * len(variantes))
        cursor.execute(
            f'SELECT COUNT(*) FROM test_moca WHERE LOWER(resultado) IN ({marcadores})',
            tuple(v.lower() for v in variantes)
        )
        return cursor.fetchone()[0]

    normal = _cuenta_moca('Normal', 'NORMAL')
    pdcl = _cuenta_moca('PDCL')
    pdcm = _cuenta_moca('PDCM', 'DC', 'PDCM / DC')
    nada_mental = _cuenta_moca('NADA MENTAL')

    query = request.args.get('q', '').strip()

    pagina = request.args.get('pagina', 1, type=int)
    if pagina < 1:
        pagina = 1
    por_pagina = 10

    cols = '''p.id, p.nombres, p.apellidos, p.edad, p.sexo,
              t.puntaje_total, t.resultado, t.evaluador, t.fecha_examen'''

    if query:
        patron = f'%{normalizar(query)}%'
        cursor.execute('SELECT COUNT(*) FROM pacientes p WHERE p.busqueda LIKE %s', (patron,))
        total_filas = cursor.fetchone()[0]
        cursor.execute(f'''
            SELECT {cols}
            FROM pacientes p
            LEFT JOIN test_moca t ON p.id = t.paciente_id
            WHERE p.busqueda LIKE %s
            ORDER BY p.apellidos, p.nombres
            LIMIT %s OFFSET %s
        ''', (patron, por_pagina, (pagina - 1) * por_pagina))
    else:
        total_filas = total_pacientes
        cursor.execute(f'''
            SELECT {cols}
            FROM pacientes p
            LEFT JOIN test_moca t ON p.id = t.paciente_id
            ORDER BY p.apellidos, p.nombres
            LIMIT %s OFFSET %s
        ''', (por_pagina, (pagina - 1) * por_pagina))

    filas = cursor.fetchall()
    columnas = [desc[0] for desc in cursor.description]
    resultados = [dict(zip(columnas, fila)) for fila in filas]
    total_paginas = max(1, -(-total_filas // por_pagina))

    conexion.close()

    return render_template(
        'test_moca_dashboard.html',
        total_tests=total_tests,
        total_pacientes=total_pacientes,
        pendientes=pendientes,
        normal=normal,
        pdcl=pdcl,
        pdcm=pdcm,
        nada_mental=nada_mental,
        query=query,
        resultados=resultados,
        pagina=pagina,
        total_paginas=total_paginas,
    )


@app.route('/test_moca_formulario', methods=['GET', 'POST'])
@login_required
def test_moca_formulario():
    """Formulario individual de Test MoCA"""
    from flask import session

    paciente_id = session.get('paciente_seleccionado_id')
    if not paciente_id:
        return redirect(url_for('seleccionar_paciente', modulo='test_moca_formulario'))

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute('SELECT * FROM pacientes WHERE id = %s AND COALESCE(activo, TRUE) = TRUE', (paciente_id,))
    paciente = cursor.fetchone()
    if not paciente:
        session.pop('paciente_seleccionado_id', None)
        return redirect(url_for('seleccionar_paciente', modulo='test_moca_formulario'))

    columnas = [desc[0] for desc in cursor.description]
    paciente_dict = dict(zip(columnas, paciente))
    _actualizar_edad_calculada(paciente_dict)

    cursor.execute('SELECT * FROM test_moca WHERE paciente_id = %s', (paciente_id,))
    test_existente = cursor.fetchone()
    valores = {}
    if test_existente:
        columnas_test = [desc[0] for desc in cursor.description]
        valores = dict(zip(columnas_test, test_existente))

    if request.method == 'POST':
        dominios = ['visuoespacial', 'denominacion', 'memoria', 'atencion',
                    'lenguaje', 'abstraccion', 'orientacion']
        # Máximos por dominio para acotar valores
        maximos = {'visuoespacial': 5, 'denominacion': 3, 'memoria': 5, 'atencion': 6,
                   'lenguaje': 3, 'abstraccion': 2, 'orientacion': 6}

        def _int(nombre, maximo):
            try:
                v = int(request.form.get(nombre, 0) or 0)
            except (TypeError, ValueError):
                v = 0
            return max(0, min(v, maximo))

        nada_mental = request.form.get('nada_mental') == 'on'

        if nada_mental:
            vals = {c: 0 for c in dominios}
            puntaje_total = 0
        else:
            vals = {c: _int(c, maximos[c]) for c in dominios}
            puntaje_total = sum(vals.values())

        # Clasificación MoCA:
        #  Normal >= 26; PDCL (deterioro cognitivo leve) 18-25; PDCM/DC < 18
        if nada_mental:
            resultado = 'NADA MENTAL'
        elif puntaje_total >= 26:
            resultado = 'Normal'
        elif puntaje_total >= 18:
            resultado = 'PDCL'
        else:
            resultado = 'PDCM'

        def _int_opt(nombre):
            v = request.form.get(nombre)
            if v is None or v == '':
                return None
            try:
                return int(v)
            except (TypeError, ValueError):
                return None

        indice_memoria = _int_opt('indice_memoria')
        evaluador = request.form.get('evaluador') or None
        observaciones = request.form.get('observaciones') or None
        fecha_examen = request.form.get('fecha_examen') or None

        valores_dom = [vals[c] for c in dominios]

        if test_existente:
            asignaciones = ', '.join(f'{c} = %s' for c in dominios)
            cursor.execute(
                f'''UPDATE test_moca SET {asignaciones},
                    puntaje_total = %s, nada_mental = %s, indice_memoria = %s,
                    resultado = %s, evaluador = %s, observaciones = %s, fecha_examen = %s
                    WHERE paciente_id = %s''',
                valores_dom + [puntaje_total, nada_mental, indice_memoria,
                               resultado, evaluador, observaciones, fecha_examen, paciente_id]
            )
        else:
            columnas_insert = ', '.join(dominios)
            placeholders = ', '.join(['%s'] * len(dominios))
            cursor.execute(
                f'''INSERT INTO test_moca (paciente_id, {columnas_insert},
                    puntaje_total, nada_mental, indice_memoria,
                    resultado, evaluador, observaciones, fecha_examen)
                    VALUES (%s, {placeholders}, %s, %s, %s, %s, %s, %s, %s)''',
                [paciente_id] + valores_dom + [puntaje_total, nada_mental, indice_memoria,
                                               resultado, evaluador, observaciones, fecha_examen]
            )

        conexion.commit()
        conexion.close()
        volver = request.form.get('volver_url') or session.pop('volver_formulario_url', None) or url_for('test_moca')
        return redirect(volver)
        volver = request.form.get('volver_url') or session.pop('volver_formulario_url', None) or url_for('test_moca')
        return redirect(volver)

    conexion.close()

    volver_url = session.pop('volver_formulario_url', None) or url_for('test_moca')
    volver_url = session.pop('volver_formulario_url', None) or url_for('test_moca')
    return render_template('test_moca.html', paciente=paciente_dict, valores=valores,
                           existe=bool(test_existente), volver_url=volver_url)


@app.route('/test_tinetti', methods=['GET', 'POST'])
@login_required
def test_tinetti():
    """Vista tipo dashboard de Test Tinetti con tabla de pacientes"""
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute('SELECT COUNT(DISTINCT paciente_id) FROM test_tinetti')
    total_tests = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM pacientes')
    total_pacientes = cursor.fetchone()[0]

    pendientes = total_pacientes - total_tests

    # Categorías de resultado (acepta 'Bajo Riesgo' y 'BAJO' de datos importados)
    def _cuenta_tin(*variantes):
        marcadores = ', '.join(['%s'] * len(variantes))
        cursor.execute(
            f'SELECT COUNT(*) FROM test_tinetti WHERE LOWER(resultado) IN ({marcadores})',
            tuple(v.lower() for v in variantes)
        )
        return cursor.fetchone()[0]

    bajo_riesgo = _cuenta_tin('Bajo Riesgo', 'BAJO')
    riesgo_moderado = _cuenta_tin('Riesgo Moderado', 'MODERADO')
    alto_riesgo = _cuenta_tin('Alto Riesgo', 'ALTO')

    query = request.args.get('q', '').strip()

    pagina = request.args.get('pagina', 1, type=int)
    if pagina < 1:
        pagina = 1
    por_pagina = 10

    cols = '''p.id, p.nombres, p.apellidos, p.edad, p.sexo,
              t.puntaje_equilibrio, t.puntaje_marcha, t.puntaje_total,
              t.resultado, t.evaluador, t.fecha_examen'''

    if query:
        patron = f'%{normalizar(query)}%'
        cursor.execute('SELECT COUNT(*) FROM pacientes p WHERE p.busqueda LIKE %s', (patron,))
        total_filas = cursor.fetchone()[0]
        cursor.execute(f'''
            SELECT {cols}
            FROM pacientes p
            LEFT JOIN test_tinetti t ON p.id = t.paciente_id
            WHERE p.busqueda LIKE %s
            ORDER BY p.apellidos, p.nombres
            LIMIT %s OFFSET %s
        ''', (patron, por_pagina, (pagina - 1) * por_pagina))
    else:
        total_filas = total_pacientes
        cursor.execute(f'''
            SELECT {cols}
            FROM pacientes p
            LEFT JOIN test_tinetti t ON p.id = t.paciente_id
            ORDER BY p.apellidos, p.nombres
            LIMIT %s OFFSET %s
        ''', (por_pagina, (pagina - 1) * por_pagina))

    filas = cursor.fetchall()
    columnas = [desc[0] for desc in cursor.description]
    resultados = [dict(zip(columnas, fila)) for fila in filas]
    total_paginas = max(1, -(-total_filas // por_pagina))

    conexion.close()

    return render_template(
        'test_tinetti_dashboard.html',
        total_tests=total_tests,
        total_pacientes=total_pacientes,
        pendientes=pendientes,
        bajo_riesgo=bajo_riesgo,
        riesgo_moderado=riesgo_moderado,
        alto_riesgo=alto_riesgo,
        query=query,
        resultados=resultados,
        pagina=pagina,
        total_paginas=total_paginas,
    )


@app.route('/test_tinetti_formulario', methods=['GET', 'POST'])
@login_required
def test_tinetti_formulario():
    """Formulario individual de Test Tinetti"""
    from flask import session

    paciente_id = session.get('paciente_seleccionado_id')
    if not paciente_id:
        return redirect(url_for('seleccionar_paciente', modulo='test_tinetti_formulario'))

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute('SELECT * FROM pacientes WHERE id = %s AND COALESCE(activo, TRUE) = TRUE', (paciente_id,))
    paciente = cursor.fetchone()
    if not paciente:
        session.pop('paciente_seleccionado_id', None)
        return redirect(url_for('seleccionar_paciente', modulo='test_tinetti_formulario'))

    columnas = [desc[0] for desc in cursor.description]
    paciente_dict = dict(zip(columnas, paciente))
    _actualizar_edad_calculada(paciente_dict)

    cursor.execute('SELECT * FROM test_tinetti WHERE paciente_id = %s', (paciente_id,))
    test_existente = cursor.fetchone()
    valores = {}
    if test_existente:
        columnas_test = [desc[0] for desc in cursor.description]
        valores = dict(zip(columnas_test, test_existente))

    if request.method == 'POST':
        items_equilibrio = ['eq_sentado', 'eq_levanta', 'eq_intenta_levantar', 'eq_inmediato_pie',
                            'eq_de_pie', 'eq_tocado', 'eq_ojos_cerrados', 'eq_giro_pasos',
                            'eq_giro_estabilidad', 'eq_sentandose']
        items_marcha = ['ma_inicio', 'ma_longitud', 'ma_altura', 'ma_simetria',
                       'ma_continuidad', 'ma_trayectoria', 'ma_equilibrio']

        def _int(nombre):
            try:
                return int(request.form.get(nombre, 0) or 0)
            except (TypeError, ValueError):
                return 0

        vals_eq = {c: _int(c) for c in items_equilibrio}
        vals_ma = {c: _int(c) for c in items_marcha}

        puntaje_equilibrio = sum(vals_eq.values())
        puntaje_marcha = sum(vals_ma.values())
        puntaje_total = puntaje_equilibrio + puntaje_marcha

        # Clasificación Tinetti (sobre 28): >=24 bajo riesgo, 19-23 moderado, <19 alto
        if puntaje_total >= 24:
            resultado = 'Bajo Riesgo'
        elif puntaje_total >= 19:
            resultado = 'Riesgo Moderado'
        else:
            resultado = 'Alto Riesgo'

        evaluador = request.form.get('evaluador') or None
        observaciones = request.form.get('observaciones') or None
        fecha_examen = request.form.get('fecha_examen') or None

        todas = items_equilibrio + items_marcha
        valores_items = [vals_eq.get(c, vals_ma.get(c, 0)) for c in todas]

        if test_existente:
            asignaciones = ', '.join(f'{c} = %s' for c in todas)
            cursor.execute(
                f'''UPDATE test_tinetti SET {asignaciones},
                    puntaje_equilibrio = %s, puntaje_marcha = %s, puntaje_total = %s,
                    resultado = %s, evaluador = %s, observaciones = %s, fecha_examen = %s
                    WHERE paciente_id = %s''',
                valores_items + [puntaje_equilibrio, puntaje_marcha, puntaje_total,
                                 resultado, evaluador, observaciones, fecha_examen, paciente_id]
            )
        else:
            columnas_insert = ', '.join(todas)
            placeholders = ', '.join(['%s'] * len(todas))
            cursor.execute(
                f'''INSERT INTO test_tinetti (paciente_id, {columnas_insert},
                    puntaje_equilibrio, puntaje_marcha, puntaje_total,
                    resultado, evaluador, observaciones, fecha_examen)
                    VALUES (%s, {placeholders}, %s, %s, %s, %s, %s, %s, %s)''',
                [paciente_id] + valores_items + [puntaje_equilibrio, puntaje_marcha, puntaje_total,
                                                 resultado, evaluador, observaciones, fecha_examen]
            )

        conexion.commit()
        conexion.close()
        volver = request.form.get('volver_url') or session.pop('volver_formulario_url', None) or url_for('test_tinetti')
        return redirect(volver)
        volver = request.form.get('volver_url') or session.pop('volver_formulario_url', None) or url_for('test_tinetti')
        return redirect(volver)

    conexion.close()

    volver_url = session.pop('volver_formulario_url', None) or url_for('test_tinetti')
    volver_url = session.pop('volver_formulario_url', None) or url_for('test_tinetti')
    return render_template('test_tinetti.html', paciente=paciente_dict, valores=valores,
                           existe=bool(test_existente), volver_url=volver_url)


@app.route('/test_chair_stand', methods=['GET', 'POST'])
@login_required
def test_chair_stand():
    """Vista tipo dashboard de Test Chair Stand con tabla de pacientes"""
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute('SELECT COUNT(DISTINCT paciente_id) FROM test_chair_stand')
    total_tests = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM pacientes')
    total_pacientes = cursor.fetchone()[0]

    pendientes = total_pacientes - total_tests

    # Categorías de resultado (case-insensitive; datos viejos vienen en MAYÚSCULAS)
    def _cuenta_chair(*variantes):
        marcadores = ', '.join(['%s'] * len(variantes))
        cursor.execute(
            f'SELECT COUNT(*) FROM test_chair_stand WHERE LOWER(resultado) IN ({marcadores})',
            tuple(v.lower() for v in variantes)
        )
        return cursor.fetchone()[0]

    muy_pobre = _cuenta_chair('Muy Pobre')
    pobre = _cuenta_chair('Pobre')
    regular = _cuenta_chair('Regular')
    promedio = _cuenta_chair('Promedio')
    alto = _cuenta_chair('Alto')
    superior = _cuenta_chair('Superior')

    query = request.args.get('q', '').strip()
    pagina = request.args.get('pagina', 1, type=int)
    if pagina < 1:
        pagina = 1
    por_pagina = 10

    if query:
        patron = f'%{normalizar(query)}%'
        cursor.execute('SELECT COUNT(*) FROM pacientes p WHERE p.busqueda LIKE %s', (patron,))
        total_filas = cursor.fetchone()[0]
        cursor.execute('''
            SELECT p.id, p.nombres, p.apellidos, p.edad, p.sexo,
                   t.repeticiones, t.percentil, t.resultado, t.evaluador, t.fecha_examen
            FROM pacientes p
            LEFT JOIN test_chair_stand t ON p.id = t.paciente_id
            WHERE p.busqueda LIKE %s
            ORDER BY p.apellidos, p.nombres
            LIMIT %s OFFSET %s
        ''', (patron, por_pagina, (pagina - 1) * por_pagina))
    else:
        total_filas = total_pacientes
        cursor.execute('''
            SELECT p.id, p.nombres, p.apellidos, p.edad, p.sexo,
                   t.repeticiones, t.percentil, t.resultado, t.evaluador, t.fecha_examen
            FROM pacientes p
            LEFT JOIN test_chair_stand t ON p.id = t.paciente_id
            ORDER BY p.apellidos, p.nombres
            LIMIT %s OFFSET %s
        ''', (por_pagina, (pagina - 1) * por_pagina))

    filas = cursor.fetchall()
    columnas = [desc[0] for desc in cursor.description]
    resultados = [dict(zip(columnas, fila)) for fila in filas]
    total_paginas = max(1, -(-total_filas // por_pagina))

    conexion.close()

    return render_template(
        'test_chair_stand_dashboard.html',
        total_tests=total_tests,
        total_pacientes=total_pacientes,
        pendientes=pendientes,
        muy_pobre=muy_pobre,
        pobre=pobre,
        regular=regular,
        promedio=promedio,
        alto=alto,
        superior=superior,
        query=query,
        resultados=resultados,
        pagina=pagina,
        total_paginas=total_paginas,
    )


@app.route('/test_chair_stand_formulario', methods=['GET', 'POST'])
@login_required
def test_chair_stand_formulario():
    """Formulario individual de Test Chair Stand"""
    from flask import session

    paciente_id = session.get('paciente_seleccionado_id')
    if not paciente_id:
        return redirect(url_for('seleccionar_paciente', modulo='test_chair_stand_formulario'))

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute('SELECT * FROM pacientes WHERE id = %s AND COALESCE(activo, TRUE) = TRUE', (paciente_id,))
    paciente = cursor.fetchone()
    if not paciente:
        session.pop('paciente_seleccionado_id', None)
        return redirect(url_for('seleccionar_paciente', modulo='test_chair_stand_formulario'))

    columnas = [desc[0] for desc in cursor.description]
    paciente_dict = dict(zip(columnas, paciente))
    _actualizar_edad_calculada(paciente_dict)

    cursor.execute('SELECT * FROM test_chair_stand WHERE paciente_id = %s', (paciente_id,))
    test_existente = cursor.fetchone()
    valores = {}
    if test_existente:
        columnas_test = [desc[0] for desc in cursor.description]
        valores = dict(zip(columnas_test, test_existente))

    if request.method == 'POST':
        try:
            repeticiones = int(request.form.get('repeticiones') or 0)
        except (TypeError, ValueError):
            repeticiones = 0

        evaluador = request.form.get('evaluador') or None
        observaciones = request.form.get('observaciones') or None
        fecha_examen = request.form.get('fecha_examen') or None
        # La edad queda fijada con la evaluación para que el resultado histórico
        # no cambie solo porque el paciente cumple años.
        edad_evaluacion = valores.get('edad_evaluacion') if valores.get('edad_evaluacion') is not None else _edad_para_evaluacion(paciente_dict, fecha_examen)

        # Clasificación clínica: cruza repeticiones con el rango normal por
        # edad y sexo del paciente (Senior Fitness Test), no una escala fija.
        resultado, percentil = clasificar_chair_stand(
            repeticiones,
            edad_evaluacion,
            paciente_dict.get('sexo'),
        )

        if test_existente:
            cursor.execute(
                '''UPDATE test_chair_stand SET repeticiones = %s, percentil = %s,
                   resultado = %s, evaluador = %s, observaciones = %s, fecha_examen = %s
                   WHERE paciente_id = %s''',
                (repeticiones, percentil, resultado, evaluador, observaciones, fecha_examen, paciente_id)
            )
        else:
            cursor.execute(
                '''INSERT INTO test_chair_stand
                   (paciente_id, repeticiones, percentil, resultado, evaluador, observaciones, fecha_examen, edad_evaluacion)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''',
                (paciente_id, repeticiones, percentil, resultado, evaluador, observaciones, fecha_examen, edad_evaluacion)
            )

        conexion.commit()
        conexion.close()
        volver = request.form.get('volver_url') or session.pop('volver_formulario_url', None) or url_for('test_chair_stand')
        return redirect(volver)
        volver = request.form.get('volver_url') or session.pop('volver_formulario_url', None) or url_for('test_chair_stand')
        return redirect(volver)

    conexion.close()

    volver_url = session.pop('volver_formulario_url', None) or url_for('test_chair_stand')
    volver_url = session.pop('volver_formulario_url', None) or url_for('test_chair_stand')
    return render_template('test_chair_stand.html', paciente=paciente_dict, valores=valores,
                           existe=bool(test_existente), volver_url=volver_url)


@app.route('/caracterizacion')
@login_required
def caracterizacion():
    """Vista tipo dashboard de Caracterización con tabla de pacientes y paginación."""
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute('SELECT COUNT(DISTINCT paciente_id) FROM caracterizacion_socioeconomica')
    total_registros = cursor.fetchone()[0]

    cursor.execute('SELECT COUNT(*) FROM pacientes')
    total_pacientes = cursor.fetchone()[0]
    pendientes = total_pacientes - total_registros

    query = request.args.get('q', '').strip()
    pagina = request.args.get('pagina', 1, type=int)
    if pagina < 1:
        pagina = 1
    por_pagina = 10

    cols = '''p.id, p.nombres, p.apellidos, p.edad, c.escolaridad, c.vivienda,
              c.con_quien_convive, c.estado_socioeconomico, c.fecha_examen'''

    if query:
        patron = f'%{normalizar(query)}%'
        cursor.execute('SELECT COUNT(*) FROM pacientes p WHERE p.busqueda LIKE %s', (patron,))
        total_filas = cursor.fetchone()[0]
        cursor.execute(f'''
            SELECT {cols}
            FROM pacientes p
            LEFT JOIN caracterizacion_socioeconomica c ON p.id = c.paciente_id
            WHERE p.busqueda LIKE %s
            ORDER BY p.apellidos, p.nombres
            LIMIT %s OFFSET %s
        ''', (patron, por_pagina, (pagina - 1) * por_pagina))
    else:
        total_filas = total_pacientes
        cursor.execute(f'''
            SELECT {cols}
            FROM pacientes p
            LEFT JOIN caracterizacion_socioeconomica c ON p.id = c.paciente_id
            ORDER BY p.apellidos, p.nombres
            LIMIT %s OFFSET %s
        ''', (por_pagina, (pagina - 1) * por_pagina))

    filas = cursor.fetchall()
    columnas = [desc[0] for desc in cursor.description]
    resultados = [dict(zip(columnas, fila)) for fila in filas]
    total_paginas = max(1, -(-total_filas // por_pagina))

    conexion.close()

    return render_template(
        'caracterizacion_dashboard.html',
        total_registros=total_registros,
        total_pacientes=total_pacientes,
        pendientes=pendientes,
        query=query,
        resultados=resultados,
        pagina=pagina,
        total_paginas=total_paginas,
    )


@app.route('/caracterizacion_socioeconomica', methods=['GET', 'POST'])
@login_required
def caracterizacion_socioeconomica():
    """Formulario de Caracterización Socioeconómica"""
    from flask import session

    paciente_id = session.get('paciente_seleccionado_id')
    if not paciente_id:
        return redirect(url_for('seleccionar_paciente', modulo='caracterizacion_socioeconomica'))

    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute('SELECT * FROM pacientes WHERE id = %s AND COALESCE(activo, TRUE) = TRUE', (paciente_id,))
    paciente = cursor.fetchone()
    if not paciente:
        session.pop('paciente_seleccionado_id', None)
        return redirect(url_for('seleccionar_paciente', modulo='caracterizacion_socioeconomica'))

    columnas = [desc[0] for desc in cursor.description]
    paciente_dict = dict(zip(columnas, paciente))

    cursor.execute('SELECT * FROM caracterizacion_socioeconomica WHERE paciente_id = %s', (paciente_id,))
    caract_existente = cursor.fetchone()
    valores = {}
    if caract_existente:
        columnas_caract = [desc[0] for desc in cursor.description]
        valores = dict(zip(columnas_caract, caract_existente))

    if request.method == 'POST':
        campos = ['escolaridad', 'vivienda', 'con_quien_convive', 'estado_socioeconomico', 'fecha_examen']
        valores_form = {campo: (request.form.get(campo) or None) for campo in campos}

        if caract_existente:
            asignaciones = ', '.join(f'{c} = %s' for c in campos if c != 'id')
            valores_update = [valores_form[c] for c in campos if c != 'id']
            cursor.execute(
                f'UPDATE caracterizacion_socioeconomica SET {asignaciones} WHERE paciente_id = %s',
                valores_update + [paciente_id]
            )
        else:
            columnas_insert = ', '.join(campos)
            placeholders = ', '.join(['%s'] * len(campos))
            cursor.execute(
                f'INSERT INTO caracterizacion_socioeconomica (paciente_id, {columnas_insert}) VALUES (%s, {placeholders})',
                [paciente_id] + [valores_form[c] for c in campos]
            )

        conexion.commit()
        conexion.close()
        volver = request.form.get('volver_url') or session.pop('volver_formulario_url', None) or url_for('caracterizacion')
        return redirect(volver)
        volver = request.form.get('volver_url') or session.pop('volver_formulario_url', None) or url_for('caracterizacion')
        return redirect(volver)

    conexion.close()

    volver_url = session.pop('volver_formulario_url', None) or url_for('caracterizacion')
    volver_url = session.pop('volver_formulario_url', None) or url_for('caracterizacion')
    return render_template('caracterizacion_socioeconomica.html', paciente=paciente_dict, valores=valores,
                           existe=bool(caract_existente), volver_url=volver_url)


if __name__ == '__main__':
    # En local: debug activo. En producción (Render) usa gunicorn, que no
    # ejecuta este bloque. El puerto se toma de la variable PORT si existe.
    puerto = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
    app.run(host='0.0.0.0', port=puerto, debug=debug)
