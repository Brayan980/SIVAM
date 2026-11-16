-- SIVAM / Supabase (PostgreSQL)
-- Ejecutar UNA sola vez en Supabase SQL Editor antes de desplegar la aplicación.
-- Los registros ya importados desde Excel permanecen con valores NULL: esto
-- expresa que no existe evidencia digital de autorización; no presume rechazo
-- ni crea evidencia retroactiva.

ALTER TABLE pacientes
    ADD COLUMN IF NOT EXISTS autoriza_tratamiento_datos BOOLEAN,
    ADD COLUMN IF NOT EXISTS fecha_autorizacion TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS version_politica TEXT,
    ADD COLUMN IF NOT EXISTS texto_autorizacion_aceptado TEXT;

ALTER TABLE pacientes
    ADD CONSTRAINT pacientes_autorizacion_consistente CHECK (
        (autoriza_tratamiento_datos IS NULL
         AND fecha_autorizacion IS NULL
         AND version_politica IS NULL
         AND texto_autorizacion_aceptado IS NULL)
        OR
        (autoriza_tratamiento_datos IS TRUE
         AND fecha_autorizacion IS NOT NULL
         AND version_politica IS NOT NULL
         AND texto_autorizacion_aceptado IS NOT NULL)
    );

CREATE TABLE IF NOT EXISTS consentimientos_tratamiento_datos (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    paciente_id INTEGER NOT NULL REFERENCES pacientes(id) ON DELETE RESTRICT,
    autoriza_tratamiento_datos BOOLEAN NOT NULL CHECK (autoriza_tratamiento_datos IS TRUE),
    fecha_autorizacion TIMESTAMPTZ NOT NULL,
    version_politica TEXT NOT NULL,
    texto_autorizacion_aceptado TEXT NOT NULL,
    registrado_por INTEGER REFERENCES usuarios(id),
    fecha_registro TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE OR REPLACE FUNCTION impedir_cambio_consentimiento()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.autoriza_tratamiento_datos IS TRUE AND (
        NEW.autoriza_tratamiento_datos IS DISTINCT FROM OLD.autoriza_tratamiento_datos OR
        NEW.fecha_autorizacion IS DISTINCT FROM OLD.fecha_autorizacion OR
        NEW.version_politica IS DISTINCT FROM OLD.version_politica OR
        NEW.texto_autorizacion_aceptado IS DISTINCT FROM OLD.texto_autorizacion_aceptado
    ) THEN
        RAISE EXCEPTION 'La autorización conservada no puede modificarse';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS pacientes_consentimiento_inalterable ON pacientes;
CREATE TRIGGER pacientes_consentimiento_inalterable
BEFORE UPDATE ON pacientes
FOR EACH ROW EXECUTE FUNCTION impedir_cambio_consentimiento();

CREATE OR REPLACE FUNCTION impedir_mutacion_evidencia_consentimiento()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'La evidencia de consentimiento es de solo inserción';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS consentimiento_solo_insercion_actualizar ON consentimientos_tratamiento_datos;
DROP TRIGGER IF EXISTS consentimiento_solo_insercion_eliminar ON consentimientos_tratamiento_datos;
CREATE TRIGGER consentimiento_solo_insercion_actualizar
BEFORE UPDATE ON consentimientos_tratamiento_datos
FOR EACH ROW EXECUTE FUNCTION impedir_mutacion_evidencia_consentimiento();
CREATE TRIGGER consentimiento_solo_insercion_eliminar
BEFORE DELETE ON consentimientos_tratamiento_datos
FOR EACH ROW EXECUTE FUNCTION impedir_mutacion_evidencia_consentimiento();

CREATE INDEX IF NOT EXISTS idx_consentimientos_paciente
    ON consentimientos_tratamiento_datos (paciente_id, fecha_autorizacion);

-- En Supabase, mantenga estas tablas fuera de políticas que permitan UPDATE o
-- DELETE al rol de la aplicación. Los triggers protegen la integridad incluso
-- cuando ese rol sí puede conectarse directamente a PostgreSQL.
