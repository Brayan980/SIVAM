# ============================================================
# VISTA DEL MEDICO - Buscador y registro de historias clinicas
# ============================================================
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, abort
from werkzeug.security import check_password_hash, generate_password_hash
from functools import wraps
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from dotenv import load_dotenv
import os
from campos import CAMPOS, CAMPOS_CLINICOS, ETIQUETAS, normalizar
from db import conectar
import exportar
import graficas

# Cargar variables de entorno
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'clave-secreta-para-sesiones')

# Configuración de Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Por favor inicia sesión para acceder a esta página.'


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


@app.route('/')
@login_required
def index():
    query = request.args.get('q', '').strip()
    paciente_id = request.args.get('id', type=int)

    resultados = []
    paciente = None

    conexion = conectar()
    cursor = conexion.cursor()

    if paciente_id:
        cursor.execute('SELECT * FROM pacientes WHERE id = %s', (paciente_id,))
        fila = cursor.fetchone()
        if fila:
            columnas = [desc[0] for desc in cursor.description]
            paciente = dict(zip(columnas, fila))

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
            cursor.execute('SELECT COUNT(*) FROM pacientes WHERE busqueda LIKE %s', (patron,))
            total_filas = cursor.fetchone()[0]
            cursor.execute(
                '''SELECT * FROM pacientes
                   WHERE busqueda LIKE %s
                   ORDER BY apellidos, nombres
                   LIMIT %s OFFSET %s''',
                (patron, por_pagina, (pagina - 1) * por_pagina)
            )
        else:
            cursor.execute('SELECT COUNT(*) FROM pacientes')
            total_filas = cursor.fetchone()[0]
            cursor.execute(
                '''SELECT * FROM pacientes
                   ORDER BY apellidos, nombres
                   LIMIT %s OFFSET %s''',
                (por_pagina, (pagina - 1) * por_pagina)
            )
        filas = cursor.fetchall()
        columnas = [desc[0] for desc in cursor.description]
        resultados = [dict(zip(columnas, fila)) for fila in filas]
        total_paginas = max(1, -(-total_filas // por_pagina))

    conexion.close()

    detalle = None
    if paciente:
        detalle = [
            (ETIQUETAS.get(campo, campo), valor)
            for campo, valor in paciente.items()
            if campo not in ('id', 'nombres', 'apellidos', 'busqueda') and valor not in (None, '')
            and campo not in ['antropometria', 'vo2_max', 'test_moca', 'test_tinetti', 'test_chair_stand', 'caracterizacion']
        ]

    return render_template(
        'index_sivam.html',
        query=query,
        resultados=resultados,
        paciente=paciente,
        detalle=detalle,
        pagina=pagina,
        total_paginas=total_paginas,
        total_registros=(total_filas if not paciente_id else 0),
    )


@app.route('/paciente/<int:paciente_id>/dashboard')
@login_required
def dashboard_paciente(paciente_id):
    """Dashboard individual de un paciente: resumen de su información y de los
    resultados de cada test (con indicadores y gráficas de medidor)."""
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute('SELECT * FROM pacientes WHERE id = %s', (paciente_id,))
    fila = cursor.fetchone()
    if not fila:
        conexion.close()
        abort(404)
    columnas = [desc[0] for desc in cursor.description]
    paciente = dict(zip(columnas, fila))

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
    conexion.close()
    return render_template('_historia_modal.html', p=p)


@app.route('/paciente_ficha/<int:paciente_id>')
@login_required
def paciente_ficha(paciente_id):
    """Devuelve el HTML de la ficha de un paciente para mostrar en un modal."""
    conexion = conectar()
    cursor = conexion.cursor()

    cursor.execute('SELECT * FROM pacientes WHERE id = %s', (paciente_id,))
    fila = cursor.fetchone()
    if not fila:
        conexion.close()
        return '<p>Paciente no encontrado.</p>', 404

    columnas = [desc[0] for desc in cursor.description]
    paciente = dict(zip(columnas, fila))

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
        if campo not in ('id', 'nombres', 'apellidos', 'busqueda') and valor not in (None, '')
    ]

    return render_template('_ficha_modal.html', paciente=paciente, detalle=detalle, modulos=modulos)


def _procesar_formulario(request_form):
    """Valida y devuelve (errores, nombres, apellidos, valores_clinicos, busqueda)."""
    errores = []
    nombres = request_form.get('nombres', '').strip()
    apellidos = request_form.get('apellidos', '').strip()

    if not nombres or not apellidos:
        errores.append('Nombres y apellidos son obligatorios.')

    valores_clinicos = [request_form.get(c, '').strip() for c in CAMPOS_CLINICOS]
    busqueda = normalizar(f'{nombres} {apellidos}')
    return errores, nombres, apellidos, valores_clinicos, busqueda


@app.route('/nuevo', methods=['GET', 'POST'])
@login_required
def nuevo():
    errores = []

    if request.method == 'POST':
        errores, nombres, apellidos, valores_clinicos, busqueda = _procesar_formulario(request.form)

        if not errores:
            conexion = conectar()
            cursor = conexion.cursor()
            columnas_insert = ', '.join(CAMPOS)
            placeholders = ', '.join(['%s'] * len(CAMPOS))
            cursor.execute(
                f'INSERT INTO pacientes ({columnas_insert}, busqueda) '
                f'VALUES ({placeholders}, %s) RETURNING id',
                [nombres, apellidos] + valores_clinicos + [busqueda]
            )
            nuevo_id = cursor.fetchone()[0]
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
    errores = []

    if request.method == 'POST':
        errores, nombres, apellidos, valores_clinicos, busqueda = _procesar_formulario(request.form)
        valores = request.form

        if not errores:
            asignaciones = ', '.join(f'{c} = %s' for c in CAMPOS)
            cursor.execute(
                f'UPDATE pacientes SET {asignaciones}, busqueda = %s WHERE id = %s',
                [nombres, apellidos] + valores_clinicos + [busqueda, paciente_id]
            )
            conexion.commit()
            conexion.close()
            return redirect(url_for('index', id=paciente_id))

    conexion.close()

    return render_template(
        'formulario_paciente_sivam.html',
        campos_clinicos=CAMPOS_CLINICOS,
        etiquetas=ETIQUETAS,
        errores=errores,
        valores=valores,
        modo='editar',
        paciente_id=paciente_id,
    )


@app.route('/eliminar/<int:paciente_id>', methods=['POST'])
@login_required
def eliminar(paciente_id):
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute('DELETE FROM pacientes WHERE id = %s', (paciente_id,))
    conexion.commit()
    conexion.close()
    return redirect(url_for('index'))


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
        cursor.execute(f'SELECT COUNT(*) FROM pacientes WHERE {filtro}', params_filtro)
        total_filas = cursor.fetchone()[0]
        cursor.execute(
            f'''SELECT id, nombres, apellidos, edad, fecha_creacion, patologia_actual,
                      ejercicio_y_actividad_fisica_leve_moderado_intenso,
                      riesgo_cardiovascular_con_riesgo_o_sin_riesgo
               FROM pacientes WHERE {filtro}
               ORDER BY apellidos, nombres LIMIT %s OFFSET %s''',
            params_filtro + (por_pagina, (pagina - 1) * por_pagina)
        )
    else:
        cursor.execute('SELECT COUNT(*) FROM pacientes')
        total_filas = cursor.fetchone()[0]
        cursor.execute(
            '''SELECT id, nombres, apellidos, edad, patologia_actual,
                      ejercicio_y_actividad_fisica_leve_moderado_intenso,
                      riesgo_cardiovascular_con_riesgo_o_sin_riesgo
               FROM pacientes
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
    conexion.close()

    usuario = getattr(current_user, 'usuario', None)
    rol = getattr(current_user, 'rol', None)

    return render_template(
        'configuracion.html',
        version='1.0.0',
        total_pacientes=total_pacientes,
        total_moca=total_moca,
        usuario=usuario,
        rol=rol,
    )
@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard con conteos reales de cada módulo"""
    conexion = conectar()
    cursor = conexion.cursor()

    # Total pacientes
    cursor.execute('SELECT COUNT(*) FROM pacientes')
    total_pacientes = cursor.fetchone()[0]

    # Historias clínicas (todos los pacientes tienen historia clínica)
    cursor.execute('SELECT COUNT(*) FROM pacientes')
    total_historias = cursor.fetchone()[0]

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
        total_historias=total_historias,
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
               WHERE busqueda LIKE %s
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
    """Fija el paciente en sesión y redirige al formulario del módulo."""
    from flask import session
    modulos_validos = {
        'antropometria': 'antropometria_formulario',
        'vo2_max': 'vo2_max_formulario',
        'test_moca': 'test_moca_formulario',
        'test_tinetti': 'test_tinetti_formulario',
        'test_chair_stand': 'test_chair_stand_formulario',
        'caracterizacion': 'caracterizacion_socioeconomica',
    }
    destino = modulos_validos.get(modulo)
    if not destino:
        return redirect(url_for('index'))
    session['paciente_seleccionado_id'] = paciente_id
    # Se llegó al formulario desde la ficha/dashboard: volver ahí (a la ficha del paciente)
    session['volver_formulario_url'] = url_for('index', id=paciente_id)
    return redirect(url_for(destino))


def _pendientes_de(tabla):
    """Devuelve los pacientes que NO tienen registro en la tabla dada."""
    conexion = conectar()
    cursor = conexion.cursor()
    cursor.execute(f'''
        SELECT p.id, p.nombres, p.apellidos, p.sexo
        FROM pacientes p
        LEFT JOIN {tabla} t ON p.id = t.paciente_id
        WHERE t.id IS NULL
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
        WHERE a.id IS NULL
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

    cursor.execute('SELECT * FROM pacientes WHERE id = %s', (paciente_id,))
    paciente = cursor.fetchone()
    if not paciente:
        session.pop('paciente_seleccionado_id', None)
        return redirect(url_for('seleccionar_paciente', modulo='antropometria_formulario'))

    columnas = [desc[0] for desc in cursor.description]
    paciente_dict = dict(zip(columnas, paciente))

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
        return redirect(url_for('antropometria'))

    conexion.close()

    volver_url = session.get('volver_formulario_url') or url_for('index', id=paciente_id)

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

    cursor.execute('SELECT * FROM pacientes WHERE id = %s', (paciente_id,))
    paciente = cursor.fetchone()
    if not paciente:
        session.pop('paciente_seleccionado_id', None)
        return redirect(url_for('seleccionar_paciente', modulo='vo2_max_formulario'))

    columnas = [desc[0] for desc in cursor.description]
    paciente_dict = dict(zip(columnas, paciente))

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
        return redirect(url_for('vo2_max'))

    conexion.close()

    volver_url = session.get('volver_formulario_url') or url_for('index', id=paciente_id)

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

    cursor.execute('SELECT * FROM pacientes WHERE id = %s', (paciente_id,))
    paciente = cursor.fetchone()
    if not paciente:
        session.pop('paciente_seleccionado_id', None)
        return redirect(url_for('seleccionar_paciente', modulo='test_moca_formulario'))

    columnas = [desc[0] for desc in cursor.description]
    paciente_dict = dict(zip(columnas, paciente))

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
        return redirect(url_for('test_moca'))

    conexion.close()

    volver_url = session.get('volver_formulario_url') or url_for('index', id=paciente_id)
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

    cursor.execute('SELECT * FROM pacientes WHERE id = %s', (paciente_id,))
    paciente = cursor.fetchone()
    if not paciente:
        session.pop('paciente_seleccionado_id', None)
        return redirect(url_for('seleccionar_paciente', modulo='test_tinetti_formulario'))

    columnas = [desc[0] for desc in cursor.description]
    paciente_dict = dict(zip(columnas, paciente))

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
        return redirect(url_for('test_tinetti'))

    conexion.close()

    volver_url = session.get('volver_formulario_url') or url_for('index', id=paciente_id)
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

    cursor.execute('SELECT * FROM pacientes WHERE id = %s', (paciente_id,))
    paciente = cursor.fetchone()
    if not paciente:
        session.pop('paciente_seleccionado_id', None)
        return redirect(url_for('seleccionar_paciente', modulo='test_chair_stand_formulario'))

    columnas = [desc[0] for desc in cursor.description]
    paciente_dict = dict(zip(columnas, paciente))

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

        # Clasificación clínica: cruza repeticiones con el rango normal por
        # edad y sexo del paciente (Senior Fitness Test), no una escala fija.
        resultado, percentil = clasificar_chair_stand(
            repeticiones,
            paciente_dict.get('edad'),
            paciente_dict.get('sexo'),
        )

        evaluador = request.form.get('evaluador') or None
        observaciones = request.form.get('observaciones') or None
        fecha_examen = request.form.get('fecha_examen') or None

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
                   (paciente_id, repeticiones, percentil, resultado, evaluador, observaciones, fecha_examen)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)''',
                (paciente_id, repeticiones, percentil, resultado, evaluador, observaciones, fecha_examen)
            )

        conexion.commit()
        conexion.close()
        return redirect(url_for('test_chair_stand'))

    conexion.close()

    volver_url = session.get('volver_formulario_url') or url_for('index', id=paciente_id)
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

    cursor.execute('SELECT * FROM pacientes WHERE id = %s', (paciente_id,))
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
        return redirect(url_for('index', id=paciente_id))

    conexion.close()

    volver_url = session.get('volver_formulario_url') or url_for('index', id=paciente_id)
    return render_template('caracterizacion_socioeconomica.html', paciente=paciente_dict, valores=valores,
                           existe=bool(caract_existente), volver_url=volver_url)


if __name__ == '__main__':
    # En local: debug activo. En producción (Render) usa gunicorn, que no
    # ejecuta este bloque. El puerto se toma de la variable PORT si existe.
    puerto = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
    app.run(host='0.0.0.0', port=puerto, debug=debug)
