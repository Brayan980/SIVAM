# Protección de datos en SIVAM

## Despliegue

1. En el SQL Editor de Supabase ejecute una sola vez `scripts/migracion/20261112_proteccion_datos.sql`.
2. Configure en el entorno de Render/Supabase de la aplicación los valores institucionales reales, antes de publicar:

   - `CONTACTO_PROTECCION_DATOS`
   - `TELEFONO_PROTECCION_DATOS`
   - `DIRECCION_PROTECCION_DATOS`

   La política muestra expresamente un aviso de configuración pendiente si estos datos no están definidos; no debe ponerse en producción con ese aviso.
3. Para la base local existente, ejecute `python scripts/migracion/migrar_proteccion_datos_local.py`. Este proceso no edita ni elimina pacientes históricos.

## Tratamiento de datos históricos

Las filas provenientes del Excel quedan con los cuatro campos de autorización en `NULL`. Esto significa que SIVAM no cuenta con prueba digital de autorización; no equivale a una autorización inferida ni se genera una fecha retroactiva. Siguen consultables para no interrumpir la operación. Cuando el titular entregue una autorización durante una edición, el operador marca la casilla y se guarda una evidencia nueva con hora UTC del servidor, texto y versión vigentes.

Los pacientes nuevos no se registran si la casilla no está marcada. Si ya existe una autorización, el formulario solo muestra su evidencia y no deja cambiarla.

## Integridad y alcance

Además de los campos de estado en `pacientes`, la tabla `consentimientos_tratamiento_datos` es un libro de evidencia de solo inserción. Los triggers de PostgreSQL rechazan actualizaciones y eliminaciones en esa evidencia e impiden modificar los campos de autorización de una ficha ya autorizada. El acceso a Supabase debe seguir el principio de mínimo privilegio: no conceder a roles de cliente permisos `UPDATE` o `DELETE` en esa tabla.

La política incluida es una implementación técnica base. CECAR debe validar sus datos de contacto, periodos de retención, encargados/transferencias y finalidades institucionales con su responsable jurídico o de protección de datos antes de su publicación definitiva.
