# Importación y preparación del Event Log

Sprint 2 convierte archivos CSV comerciales en casos y eventos normalizados sin implementar todavía algoritmos de Process Mining.

```text
CSV
  → validación estructural y por fila
  → normalización temporal y textual
  → preview sin persistencia
  → confirmación y revalidación
  → transacción única
  → commercial_cases + events + event_log_imports
```

## Contrato CSV

La cabecera mínima es:

```csv
case_code,stage_code,activity,timestamp
```

El formato completo es:

```csv
case_code,stage_code,activity,timestamp,resource,event_type,source,metadata
CASE-001,LEAD,Lead creado,2026-09-01T09:00:00-05:00,Asesor 01,STAGE_CHANGE,META_ADS,"{}"
CASE-001,CONTACTED,Lead contactado,2026-09-01T09:15:00-05:00,Asesor 01,STAGE_CHANGE,META_ADS,"{""channel"":""whatsapp""}"
```

Reglas:

- solo `.csv`, máximo 10 MB y encoding UTF-8/UTF-8-SIG;
- `case_code`, `stage_code`, `activity` y `timestamp` no pueden faltar ni estar vacíos;
- la etapa debe existir y estar activa;
- `event_type` admite `STAGE_CHANGE`, `INTERACTION` y `SYSTEM`;
- `event_type` vacío se convierte en `STAGE_CHANGE`;
- `metadata` vacío se convierte en `{}` y, cuando existe, debe ser un objeto JSON;
- timestamps con zona se convierten a UTC; timestamps sin zona se interpretan como UTC;
- una fila completamente vacía es inválida;
- las filas duplicadas dentro del mismo archivo impiden el commit.

Una sola fila inválida deshabilita la importación completa. No existe importación parcial.

## Preview

`POST /api/v1/imports/preview` recibe `multipart/form-data` con el campo `file` y no ejecuta escrituras. Devuelve conteos, errores con número de fila y hasta 20 filas válidas como muestra.

El preview consulta el catálogo actual de `process_stages`, por lo que una etapa desactivada se reporta antes de confirmar.

## Commit transaccional

`POST /api/v1/imports/commit` recibe nuevamente el archivo original y repite todas las validaciones. Dentro de una sola transacción:

1. registra `event_log_imports`;
2. recupera casos existentes;
3. crea casos faltantes;
4. omite fingerprints ya persistidos;
5. agrega los eventos nuevos;
6. recalcula la etapa actual según el último `STAGE_CHANGE` cronológico;
7. confirma todos los cambios.

Ante cualquier error inesperado se ejecuta `rollback`, incluyendo el registro de importación, casos y eventos.

Para casos nuevos:

- `started_at` es el timestamp del primer evento;
- `source` es la primera fuente no vacía;
- `assigned_resource` es el primer recurso no vacío;
- `status` inicia en `ACTIVE`;
- la etapa actual corresponde al último `STAGE_CHANGE` cronológico.

Los casos existentes conservan `source`, `started_at`, `status` y recurso. Solo se agregan eventos nuevos y se recalcula la etapa actual con el historial completo.

## Deduplicación

Hay dos niveles:

1. SHA-256 del archivo completo. Un hash ya registrado produce HTTP `409`.
2. SHA-256 semántico por evento. Se calcula sobre JSON canónico con:
   - `case_code` y `stage_code` normalizados a mayúsculas;
   - actividad sin espacios exteriores;
   - timestamp convertido a UTC;
   - tipo, recurso y fuente;
   - metadata ordenada de forma determinística.

El fingerprint es único cuando no es `null`. Los eventos manuales de Sprint 1 permanecen compatibles porque no reciben fingerprint automáticamente.

## Event Log normalizado

`GET /api/v1/event-log` devuelve:

- `case_code`
- `stage_code`
- `activity`
- `timestamp`
- `resource`
- `event_type`

El orden es `case_code ASC, timestamp ASC`. En Sprint 3 la correspondencia prevista será:

| API | Process Mining |
|---|---|
| `case_code` | `case:concept:name` |
| `activity` | `concept:name` |
| `timestamp` | `time:timestamp` |

## Dataset ficticio

El generador produce por defecto 400 casos con seed 42, fuentes y asesores ficticios. Crea recorridos normales, etapas omitidas, reprocesos, retrocesos y demoras prolongadas. Estas variantes no se clasifican dentro de la aplicación; el escenario solo aparece en el archivo ground truth separado.

```bash
python backend/scripts/generate_demo_event_log.py --cases 400 --seed 42 --output data/demo_event_log.csv
```

Los datasets locales están ignorados por Git y no contienen información personal real.
