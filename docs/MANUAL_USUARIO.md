# Manual de Usuario — SIVAM (CECAR)

**Sistema de Vista Médica: Historias Clínicas y Evaluaciones**
Versión 1.0.0

---

## Índice

1. [¿Qué es SIVAM?](#1-qué-es-sivam)
2. [Antes de empezar](#2-antes-de-empezar)
3. [Iniciar y cerrar sesión](#3-iniciar-y-cerrar-sesión)
4. [Roles y permisos](#4-roles-y-permisos)
5. [Recorrido general de la pantalla](#5-recorrido-general-de-la-pantalla)
6. [El Dashboard (panel principal)](#6-el-dashboard-panel-principal)
7. [Buscar pacientes](#7-buscar-pacientes)
8. [Historias clínicas](#8-historias-clínicas)
9. [Crear, editar y eliminar un paciente](#9-crear-editar-y-eliminar-un-paciente)
10. [Dashboard individual del paciente](#10-dashboard-individual-del-paciente)
11. [Los módulos de evaluación](#11-los-módulos-de-evaluación)
    - [11.1 Antropometría](#111-antropometría)
    - [11.2 VO2 Max](#112-vo2-max)
    - [11.3 Test MoCA](#113-test-moca)
    - [11.4 Test Tinetti](#114-test-tinetti)
    - [11.5 Test Chair Stand](#115-test-chair-stand)
    - [11.6 Caracterización socioeconómica](#116-caracterización-socioeconómica)
12. [Reporte de pendientes](#12-reporte-de-pendientes)
13. [Exportar a Excel](#13-exportar-a-excel)
14. [Gestión de usuarios (solo admin)](#14-gestión-de-usuarios-solo-admin)
15. [Configuración](#15-configuración)
16. [Preguntas frecuentes y solución de problemas](#16-preguntas-frecuentes-y-solución-de-problemas)
17. [Glosario](#17-glosario)

---

## 1. ¿Qué es SIVAM?

SIVAM es una aplicación web para registrar y consultar **historias clínicas** de pacientes y llevar el control de sus **evaluaciones médicas y físicas**.

Con SIVAM puedes:

- Registrar pacientes y su historia clínica completa.
- Aplicar y guardar seis tipos de evaluación: **Antropometría, VO2 Max, MoCA, Tinetti, Chair Stand** y **Caracterización socioeconómica**.
- Ver el resultado de cada test con indicadores de color (bueno / medio / malo) y gráficas tipo medidor.
- Consultar un **dashboard** con estadísticas generales de toda la población atendida.
- Saber qué pacientes tienen exámenes **pendientes**.
- Exportar la información a **Excel**, ya sea de un paciente o de toda la base.

Todo funciona desde el navegador. No necesitas instalar nada en tu computador para usarla.

---

## 2. Antes de empezar

Para trabajar con SIVAM solo necesitas:

- Un **navegador web** actualizado (Chrome, Edge, Firefox).
- La **dirección web** del sistema (te la da el administrador).
- Tu **usuario y contraseña**.

> Consejo: guarda la dirección del sistema en los marcadores del navegador para entrar más rápido.

---

## 3. Iniciar y cerrar sesión

### Iniciar sesión

1. Abre la dirección del sistema en tu navegador.
2. Verás la pantalla de **inicio de sesión**.
3. Escribe tu **usuario** y tu **contraseña**.
4. Pulsa **Iniciar sesión**.

Si los datos son correctos entrarás directamente al **Dashboard**. Si te equivocas, aparecerá el mensaje "Usuario o contraseña incorrectos" y podrás intentarlo de nuevo.

> El sistema no te deja entrar a ninguna página sin haber iniciado sesión. Si intentas abrir un enlace directo, te pedirá el login primero.

### Cerrar sesión

Busca la opción **Cerrar sesión** (normalmente en el menú superior o lateral) y pulsa. Volverás a la pantalla de login. Cierra siempre la sesión cuando termines, sobre todo en equipos compartidos.

---

## 4. Roles y permisos

Cada usuario tiene un **rol** que define qué puede hacer:

| Rol | Puede hacer |
|-----|-------------|
| **Médico** | Buscar, crear, editar y eliminar pacientes; aplicar todos los módulos de evaluación; ver dashboards; exportar a Excel; ver pendientes. |
| **Admin** | Todo lo del médico **más** la gestión de usuarios (crear, editar y eliminar cuentas). |

Si intentas entrar a una sección que no te corresponde (por ejemplo, la gestión de usuarios sin ser admin), el sistema muestra una página de **acceso denegado (403)**.

---

## 5. Recorrido general de la pantalla

Una vez dentro, la aplicación tiene una estructura común en todas sus páginas:

- **Menú de navegación**: te lleva al Dashboard, a la búsqueda de pacientes, a las historias clínicas, a los módulos de evaluación, al reporte de pendientes y a la configuración.
- **Área de contenido**: donde se muestran las tablas, formularios y gráficas.
- **Mensajes del sistema**: avisos que aparecen tras una acción (por ejemplo "Usuario creado correctamente"). Pueden ser de confirmación (verde) o de error (rojo).

---

## 6. El Dashboard (panel principal)

El Dashboard es la primera pantalla al entrar. Ofrece una **vista general de toda la población** registrada:

- **Totales**: número de pacientes, de historias clínicas y de evaluaciones realizadas por cada módulo (Antropometría, VO2 Max, Chair Stand, Tinetti, MoCA y Caracterización).
- **Gráficas de distribución**, por ejemplo:
  - IMC por categorías (Bajo peso, Normal, Sobrepeso, Obesidad).
  - Resultados de cada test (por niveles).
  - Riesgo cardiovascular.
  - Estado socioeconómico.

Estas gráficas te dan una idea rápida del estado del grupo de pacientes sin tener que abrir cada ficha.

---

## 7. Buscar pacientes

La búsqueda es el punto de partida para trabajar con un paciente.

1. Ve a la pantalla principal de búsqueda.
2. Escribe en la caja de búsqueda el **nombre o apellido** del paciente.
3. Pulsa Enter o el botón de buscar.

Aparecerá una lista con los resultados, ordenada por apellidos y nombres. Los resultados se muestran de **10 en 10** (paginación); usa los controles de página para avanzar.

> La búsqueda ignora mayúsculas y acentos, así que puedes escribir "jose" y encontrar "José".

Al hacer clic en un paciente verás su ficha con todos los datos registrados y accesos a sus evaluaciones.

---

## 8. Historias clínicas

La sección **Historia clínica** muestra un listado en tabla de todos los pacientes con datos clave: nombre, edad, patología actual, nivel de actividad física y riesgo cardiovascular.

- Puedes **buscar** dentro del listado por nombre, apellido, patología, barrio o riesgo cardiovascular.
- El listado también está paginado (10 por página).
- Desde aquí puedes abrir la ficha de cada paciente y exportar sus datos.

---

## 9. Crear, editar y eliminar un paciente

### Crear un paciente nuevo

1. Pulsa la opción **Nuevo** / **Nuevo paciente**.
2. Se abre el **formulario de paciente**.
3. Completa los campos. **Nombres y apellidos son obligatorios**; el resto de campos clínicos son opcionales pero se recomienda llenar todo lo que se tenga.
4. Pulsa **Guardar**.

El sistema crea el paciente y te lleva a su ficha. Si faltan nombres o apellidos, mostrará el aviso "Nombres y apellidos son obligatorios" y no guardará hasta corregirlo.

### Editar un paciente

1. Abre la ficha del paciente.
2. Pulsa **Editar**.
3. Modifica los campos que necesites.
4. Pulsa **Guardar**.

### Eliminar un paciente

1. Desde la ficha o el listado, usa la opción **Eliminar**.
2. Confirma la acción.

> ⚠️ **La eliminación es permanente.** Al borrar un paciente se pierde su información. Asegúrate antes de confirmar, y considera exportar sus datos a Excel si quieres conservar un respaldo.

---

## 10. Dashboard individual del paciente

Cada paciente tiene su propio **dashboard**, que resume su información y el resultado de cada evaluación aplicada.

Muestra **tarjetas tipo medidor** para cada test, con:

- El **valor** obtenido (por ejemplo el IMC o el puntaje del MoCA).
- El **nivel o resultado** (por ejemplo "Normal", "Alto Riesgo").
- Un **color** que indica el estado:
  - 🟢 **Bueno** (verde)
  - 🟡 **Medio** (amarillo)
  - 🔴 **Malo** (rojo)

También indica **cuántas evaluaciones** se le han realizado de las seis disponibles, para saber de un vistazo qué le falta.

---

## 11. Los módulos de evaluación

Todos los módulos siguen el mismo flujo de trabajo:

1. **Seleccionas el paciente** al que le vas a aplicar la evaluación.
2. **Llenas el formulario** del test.
3. **Guardas** y el sistema calcula automáticamente el **resultado / clasificación**.

> Para empezar cualquier módulo, primero se elige el paciente en la pantalla de **selección de paciente** (búsqueda por nombre). Así el resultado queda asociado a la persona correcta.

A continuación se explica cada módulo.

### 11.1 Antropometría

Mide la composición corporal y el riesgo asociado. Registras datos como peso, talla, circunferencia de cintura y de cadera, entre otros.

El sistema calcula automáticamente:

- **IMC (Índice de Masa Corporal)**, con su categoría:
  - Bajo peso: menor a 18.5 🟡
  - Normal: 18.5 a 24.9 🟢
  - Sobrepeso: 25 a 29.9 🟡
  - Obesidad: 30 o más 🔴
- **Índice Cintura-Cadera (ICC)**, con su nivel de riesgo (Alto 🔴 / normal 🟢) según el sexo.
- **Riesgo cardiovascular**.

### 11.2 VO2 Max

Mide la **capacidad aeróbica** (consumo máximo de oxígeno). Se registra el valor de VO2 Max y el sistema lo clasifica según **edad y sexo** en:

- Superior 🟢
- Excelente 🟢
- Bueno 🟢
- Regular 🟡
- Bajo 🔴

### 11.3 Test MoCA

Evaluación cognitiva (Montreal Cognitive Assessment). Se registra el puntaje total (escala de **0 a 30**). Clasificaciones habituales:

- **Normal** 🟢
- **PDCL** (posible deterioro cognitivo leve) 🟡
- **PDCM** (posible deterioro cognitivo moderado) 🔴

### 11.4 Test Tinetti

Evalúa el **equilibrio y la marcha** para estimar el riesgo de caídas (escala de **0 a 28**). Resultado:

- **Bajo Riesgo** 🟢
- **Riesgo Moderado** 🟡
- **Alto Riesgo** 🔴

### 11.5 Test Chair Stand

Mide la **fuerza y resistencia de las piernas** contando las repeticiones de sentarse y levantarse de una silla. El sistema clasifica el número de repeticiones según **edad y sexo**:

- Superior / Alto / Promedio 🟢
- Regular 🟡
- Pobre / Muy Pobre 🔴

### 11.6 Caracterización socioeconómica

Registra el contexto social del paciente (por ejemplo estado socioeconómico y otros datos del entorno). Se usa para análisis de la población en el Dashboard general.

---

## 12. Reporte de pendientes

Esta sección te dice **qué exámenes le faltan a cada paciente**.

1. Entra a **Reporte de pendientes**.
2. Marca los **exámenes** que quieres revisar (por defecto se muestran todos).
3. Opcionalmente, **busca** un paciente por nombre.
4. El reporte muestra, por cada paciente, una marca de **OK** (ya tiene el examen) o **falta**.

Al final verás cuántos pacientes están **completos** y cuántos tienen **pendientes**. Es la forma más rápida de organizar el trabajo del día: sabes exactamente a quién le falta cada prueba.

---

## 13. Exportar a Excel

SIVAM genera archivos Excel listos para descargar.

### Exportar un solo paciente

Desde la ficha o el listado del paciente, usa **Exportar** (paciente individual). Se descarga un Excel con una hoja por cada módulo que tenga registrado.

### Exportar toda la base

Usa la opción **Exportar datos**. Se descarga un Excel con **todos los pacientes**, organizado en una hoja por módulo (Antropometría, VO2 Max, MoCA, etc.).

> El archivo se descarga con un nombre que identifica al paciente o indica que es la base completa. Ábrelo con Excel o cualquier hoja de cálculo compatible.

---

## 14. Gestión de usuarios (solo admin)

> Esta sección solo está disponible para usuarios con rol **admin**.

En **Usuarios** puedes administrar las cuentas del sistema.

### Crear un usuario

1. Entra a **Usuarios**.
2. Completa el usuario, la contraseña, el **rol** (admin o médico) y, si quieres, el nombre completo.
3. Guarda. Si el nombre de usuario ya existe, el sistema avisa y no lo crea.

### Editar un usuario

Puedes cambiar el rol, el nombre completo y (opcionalmente) la contraseña. Si dejas la contraseña en blanco, se mantiene la actual.

### Eliminar un usuario

Usa la opción de eliminar en la fila del usuario.

**Reglas de seguridad importantes:**

- No puedes **eliminar tu propia cuenta** mientras estás conectado.
- No puedes **eliminar ni quitarle el rol admin al último administrador**. Siempre debe quedar al menos un admin en el sistema.

---

## 15. Configuración

La página de **Configuración** muestra información del sistema:

- **Versión** de la aplicación.
- **Total de pacientes** registrados.
- Total de pruebas MoCA aplicadas.
- Tu **usuario** y tu **rol** actuales.

Es una vista informativa para conocer el estado general de la instalación.

---

## 16. Preguntas frecuentes y solución de problemas

**No puedo iniciar sesión.**
Verifica que el usuario y la contraseña sean correctos (revisa mayúsculas). Si el problema sigue, pide a un administrador que restablezca tu contraseña desde **Usuarios → Editar**.

**Me aparece "Acceso denegado" (error 403).**
Estás intentando entrar a una sección solo para administradores. Si necesitas ese acceso, pídele a un admin que cambie tu rol.

**Busqué a un paciente y no aparece.**
Prueba con solo el nombre o solo el apellido. La búsqueda ignora acentos y mayúsculas. Si aun así no aparece, es posible que no esté registrado: créalo desde **Nuevo**.

**Guardé una evaluación pero no veo el resultado.**
Asegúrate de haber seleccionado el paciente correcto antes de llenar el formulario. Revisa el dashboard individual del paciente: ahí se muestran las tarjetas con el resultado calculado.

**Eliminé un paciente por error.**
La eliminación es permanente. Contacta al administrador por si existe una copia de seguridad de la base de datos.

**La sesión se cerró sola.**
Por seguridad, tras un tiempo de inactividad se puede pedir el login de nuevo. Vuelve a iniciar sesión.

---

## 17. Glosario

- **IMC**: Índice de Masa Corporal, relaciona peso y talla para clasificar el estado nutricional.
- **ICC**: Índice Cintura-Cadera, indicador de riesgo por distribución de grasa.
- **VO2 Max**: consumo máximo de oxígeno; mide la capacidad aeróbica.
- **MoCA**: prueba de evaluación cognitiva (0–30 puntos).
- **Tinetti**: prueba de equilibrio y marcha para riesgo de caídas (0–28 puntos).
- **Chair Stand**: prueba de fuerza de piernas por repeticiones sentarse/levantarse.
- **Caracterización socioeconómica**: registro del contexto social del paciente.
- **Rol**: nivel de permisos de un usuario (admin o médico).
- **Dashboard**: panel con resúmenes y gráficas.
- **Pendiente**: examen que un paciente aún no tiene registrado.

---

*Manual de usuario de SIVAM — CECAR. Versión 1.0.0.*
