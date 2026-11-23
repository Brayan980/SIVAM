-- SIVAM: estandariza el responsable de la evaluación en los seis módulos.
-- Ejecutar una vez en el SQL Editor de Supabase antes de desplegar el código.

ALTER TABLE antropometria
    ADD COLUMN IF NOT EXISTS evaluador TEXT;

ALTER TABLE vo2_max
    ADD COLUMN IF NOT EXISTS evaluador TEXT;

ALTER TABLE caracterizacion_socioeconomica
    ADD COLUMN IF NOT EXISTS evaluador TEXT;
