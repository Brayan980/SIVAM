# Fórmulas y clasificaciones de los tests — SIVAM

Este documento reúne **todas las fórmulas y reglas de clasificación** usadas en los
módulos de evaluación, indicando el **archivo exacto** y la **línea de código** donde
se encuentran, para facilitar futuros cambios.

> ⚠️ **Importante:** algunas clasificaciones están **duplicadas** en dos archivos
> (backend + gráfica, o backend + frontend). Si cambias un umbral, debes editarlo en
> **todos** los lugares indicados o los resultados quedarán inconsistentes. Al final
> del documento hay una tabla resumen de duplicaciones.

Las líneas son aproximadas (±2) porque pueden moverse al editar el código. Usa el
nombre de la función o el texto citado para localizar el bloque exacto.

---

## 1. Antropometría

### 1.1 IMC (Índice de Masa Corporal)

**Fórmula:** `IMC = peso(kg) / (talla_m)²`, donde `talla_m = talla_cm / 100`.

| Qué | Archivo | Línea aprox. | Referencia |
|-----|---------|--------------|------------|
| Cálculo (JavaScript, en el navegador) | `templates/antropometria.html` | ~190-192 | función `calcularIMC()` |
| Clasificación en vivo (etiqueta bajo el campo) | `templates/antropometria.html` | ~195-199 | dentro de `calcularIMC()` |
| Clasificación (tarjeta del dashboard del paciente) | `app.py` | ~415-422 | dentro del armado de `tarjetas` |
| Conteos por categoría (dashboard general) | `app.py` | ~927-934 | consultas `SELECT COUNT(*) ... WHERE imc ...` |
| Conteos por categoría (reporte de pendientes) | `app.py` | ~1032-1042 | consultas `SELECT COUNT(*) ... WHERE imc ...` |

**Cálculo (`templates/antropometria.html`):**
```javascript
const tm = t / 100;
const valor = p / (tm * tm);   // IMC = peso / (talla_m)^2
```

**Clasificación (mismos cortes en frontend y backend):**
```
< 18.5        → Bajo peso
18.5 a 24.9   → Normal
25 a 29.9     → Sobrepeso
>= 30         → Obesidad
```

### 1.2 ICC (Índice Cintura-Cadera)

**Fórmula:** `ICC = cintura / cadera` (redondeado a 2 decimales).

| Qué | Archivo | Línea aprox. | Referencia |
|-----|---------|--------------|------------|
| Cálculo | `exportar.py` | ~207 | función `_calcular_icc()` |
| Clasificación por sexo (OMS) | `exportar.py` | ~222 | función `_clasificar_icc()` |
| Clasificación replicada (lista Historia Clínica) | `app.py` | ~1090-1097 | dentro del bucle `for r in resultados` |
| Uso en tarjeta del dashboard | `app.py` | ~430-433 | llama a `exportar._calcular_icc` / `_clasificar_icc` |

**Clasificación (umbrales OMS por sexo):**
```
Hombre:  ICC >= 0.90 → Alto,  si no → Normal
Mujer:   ICC >= 0.85 → Alto,  si no → Normal
```

---

## 2. VO2 Max

Fuente de verdad única: **`graficas.py`**.

| Qué | Archivo | Línea aprox. | Referencia |
|-----|---------|--------------|------------|
| Tabla normativa por sexo y edad | `graficas.py` | ~40 | constante `VO2_TABLA` |
| Selección de fila según edad/sexo | `graficas.py` | ~62 | función `_vo2_fila()` |
| Clasificación cualitativa | `graficas.py` | ~87 | función `clasificar_vo2_max()` |
| Bandas de la gráfica del reporte | `graficas.py` | ~230 | función `_bandas_vo2()` |
| Aplicación al guardar la prueba | `app.py` | ~1424 | `valores_form['resultado'] = clasificar_vo2_max(...)` |

**Tabla `VO2_TABLA`** — cada fila es `(edad_min, edad_max, superior, excelente, bueno, regular)`.
Cada número es el **límite inferior (>=)** para alcanzar esa categoría. Si no llega a "regular" → **Bajo**.

**Hombres:**
```
0-29:   Superior≥55.4  Excelente≥51.1  Bueno≥45.4  Regular≥41.7
30-39:  54.0   48.3   44.0   40.5
40-49:  52.5   46.4   42.4   38.5
50-59:  48.9   43.4   39.2   35.6
60-69:  45.7   39.5   35.5   32.3
70+:    42.1   36.7   32.3   29.4
```

**Mujeres:**
```
0-29:   49.6   43.9   39.5   36.1
30-39:  47.4   42.4   37.8   34.4
40-49:  45.3   39.7   36.3   33.0
50-59:  41.1   36.7   33.0   30.1
60-69:  37.8   33.0   30.0   27.5
70+:    36.7   30.9   28.1   25.9
```

**Lógica de clasificación (`clasificar_vo2_max`):**
```
valor >= superior   → Superior
valor >= excelente  → Excelente
valor >= bueno      → Bueno
valor >= regular    → Regular
si no               → Bajo
```

> Nota: sin edad no se puede clasificar (la función devuelve `None`) y la gráfica se omite.

---

## 3. MoCA (0 a 30)

**Fórmula del puntaje:** suma de todos los dominios.

| Qué | Archivo | Línea aprox. | Referencia |
|-----|---------|--------------|------------|
| Suma del puntaje total | `app.py` | ~1591 | `puntaje_total = sum(vals.values())` |
| Clasificación | `app.py` | ~1596-1602 | tras el comentario "Clasificación MoCA" |
| Bandas de la gráfica del reporte | `graficas.py` | ~343 | función `grafica_moca()` |

**Clasificación (`app.py`):**
```
nada_mental          → NADA MENTAL
>= 26                → Normal
18 a 25              → PDCL (posible deterioro cognitivo leve)
< 18                 → PDCM (posible deterioro cognitivo moderado)
```

**Bandas de la gráfica (`graficas.py`, `grafica_moca`):**
```
0 a 18   → Deterioro
18 a 26  → Leve
26 a 30  → Normal
```

---

## 4. Tinetti (0 a 28)

**Fórmula del puntaje:** `puntaje_total = puntaje_equilibrio + puntaje_marcha`.

| Qué | Archivo | Línea aprox. | Referencia |
|-----|---------|--------------|------------|
| Suma equilibrio + marcha | `app.py` | ~1783 | `puntaje_total = puntaje_equilibrio + puntaje_marcha` |
| Clasificación | `app.py` | ~1786-1791 | tras el comentario "Clasificación Tinetti" |
| Bandas de la gráfica del reporte | `graficas.py` | ~357 | función `grafica_tinetti()` |

**Clasificación (`app.py`):**
```
>= 24    → Bajo Riesgo
19 a 23  → Riesgo Moderado
< 19     → Alto Riesgo
```

**Bandas de la gráfica (`graficas.py`, `grafica_tinetti`):**
```
0 a 19   → Alto riesgo
19 a 24  → Riesgo moderado
24 a 28  → Bajo riesgo
```

---

## 5. Chair Stand (repeticiones)

Fuente de verdad única: **`graficas.py`** (Senior Fitness Test, Rikli & Jones).

| Qué | Archivo | Línea aprox. | Referencia |
|-----|---------|--------------|------------|
| Tabla de rango normal por sexo y edad | `graficas.py` | ~104 | constante `CHAIR_STAND_TABLA` |
| Selección de rango según edad/sexo | `graficas.py` | ~130 | función `_chair_stand_rango()` |
| Clasificación cualitativa | `graficas.py` | ~159 | función `clasificar_chair_stand()` |
| Escala genérica de respaldo (sin edad) | `graficas.py` | ~173-185 | dentro de `clasificar_chair_stand()` |
| Bandas de la gráfica del reporte | `graficas.py` | ~199 | función `_bandas_chair_stand()` |
| Aplicación al guardar la prueba | `app.py` | ~1956 | `resultado, percentil = clasificar_chair_stand(...)` |

**Tabla `CHAIR_STAND_TABLA`** — cada fila es `(edad_min, edad_max, normal_bajo, normal_alto)`:

**Hombres:**
```
0-64: 14-19 · 65-69: 12-18 · 70-74: 12-17 · 75-79: 11-17 · 80-84: 10-15 · 85-89: 8-14 · 90+: 7-12
```
**Mujeres:**
```
0-64: 12-17 · 65-69: 11-16 · 70-74: 10-15 · 75-79: 10-15 · 80-84: 9-14 · 85-89: 8-13 · 90+: 4-11
```

**Lógica de clasificación (`clasificar_chair_stand`)** con
`ancho = normal_alto − normal_bajo` (mínimo 1) y `medio = (normal_bajo + normal_alto) / 2`:
```
repeticiones < normal_bajo − ancho    → Muy Pobre (percentil 5)
repeticiones < normal_bajo            → Pobre     (percentil 20)
repeticiones < medio                  → Regular   (percentil 40)
repeticiones <= normal_alto           → Promedio  (percentil 55)
repeticiones <= normal_alto + ancho   → Alto      (percentil 80)
si no                                 → Superior  (percentil 95)
```

**Escala genérica de respaldo (cuando NO hay edad):**
```
<= 10   → Muy Pobre (10)
== 11   → Pobre     (25)
== 12   → Regular   (50)
== 13   → Promedio  (60)
<= 15   → Alto      (85)
si no   → Superior  (95)
```

---

## 6. Caracterización socioeconómica

Sin fórmula ni clasificación por niveles: es **registro descriptivo** del contexto
social del paciente.

---

## 7. Resumen de duplicaciones (¡cuidado al editar!)

Si cambias un umbral, edítalo en **todos** los lugares de la fila:

| Clasificación | Lugar 1 | Lugar 2 |
|---------------|---------|---------|
| **IMC** | `app.py` ~415-422 (backend) | `templates/antropometria.html` ~195-199 (frontend JS) |
| **IMC (conteos)** | `app.py` ~927-934 | `app.py` ~1032-1042 |
| **ICC** | `exportar.py` ~222 (`_clasificar_icc`) | `app.py` ~1090-1097 |
| **VO2 Max** | `graficas.py` ~87 (`clasificar_vo2_max`) — único | bandas gráfica `graficas.py` ~230 |
| **MoCA** | `app.py` ~1596-1602 (backend) | bandas gráfica `graficas.py` ~343 |
| **Tinetti** | `app.py` ~1786-1791 (backend) | bandas gráfica `graficas.py` ~357 |
| **Chair Stand** | `graficas.py` ~159 (`clasificar_chair_stand`) — único | bandas gráfica `graficas.py` ~199 |

VO2 Max y Chair Stand tienen su lógica centralizada en `graficas.py` (una sola fuente
de verdad para el cálculo), pero las **bandas de la gráfica** del reporte se definen
aparte, por lo que también deben mantenerse alineadas.
