# Base de datos — Sprint 1

Sprint 1 define el dominio mínimo para construir un Event Log comercial persistente. El esquema se administra exclusivamente con Alembic y actualmente contiene tres tablas de aplicación.

## Relaciones

```text
PROCESS_STAGES
  ├──< COMMERCIAL_CASES.current_stage_id
  └──< EVENTS.stage_id

COMMERCIAL_CASES
  └──< EVENTS.case_id
```

Las relaciones usan `ON DELETE RESTRICT`. Esto evita eliminar accidentalmente una etapa o un caso que ya forme parte del historial. La API no expone operaciones de borrado físico; una etapa se retira configurando `active = false`.

## `process_stages`

Catálogo configurable de etapas del proceso comercial.

| Columna | Tipo | Reglas |
|---|---|---|
| `id` | UUID | Clave primaria. |
| `code` | VARCHAR(50) | Obligatorio, único e indexado. |
| `name` | VARCHAR(100) | Obligatorio. |
| `sequence` | INTEGER | Obligatorio, positivo y único. |
| `sla_hours` | INTEGER | Obligatorio y positivo. |
| `active` | BOOLEAN | `true` por defecto. |
| `created_at` | TIMESTAMPTZ | Generado automáticamente. |
| `updated_at` | TIMESTAMPTZ | Generado y actualizado automáticamente por la aplicación. |

El seed inicial incorpora:

| Secuencia | Código | Nombre | SLA inicial |
|---:|---|---|---:|
| 1 | `LEAD` | Lead | 1 h |
| 2 | `CONTACTED` | Contactado | 48 h |
| 3 | `QUALIFIED` | Calificado | 72 h |
| 4 | `VISIT` | Visita | 120 h |
| 5 | `RESERVED` | Separación | 120 h |
| 6 | `CONTRACT` | Minuta | 120 h |

Estos valores permanecen editables. Volver a ejecutar el seed no sobrescribe cambios ni duplica filas.

## `commercial_cases`

Representa una instancia individual del proceso comercial.

| Columna | Tipo | Reglas |
|---|---|---|
| `id` | UUID | Clave primaria. |
| `case_code` | VARCHAR(100) | Obligatorio, único e indexado. |
| `current_stage_id` | UUID | FK a `process_stages.id`, `RESTRICT`. |
| `assigned_resource` | VARCHAR(150) | Opcional; texto durante este sprint. |
| `source` | VARCHAR(100) | Opcional. |
| `status` | ENUM | `ACTIVE`, `CLOSED` o `CANCELLED`. |
| `started_at` | TIMESTAMPTZ | Obligatorio. |
| `closed_at` | TIMESTAMPTZ | Opcional; no puede preceder a `started_at`. |
| `created_at` | TIMESTAMPTZ | Generado automáticamente. |
| `updated_at` | TIMESTAMPTZ | Se actualiza también con cada cambio de etapa. |

No existe todavía una entidad de clientes o usuarios. `assigned_resource` no es una clave foránea en este sprint.

## `events`

Registro inmutable de actividades de cada caso y base del futuro Event Log.

| Columna | Tipo | Reglas |
|---|---|---|
| `id` | UUID | Clave primaria. |
| `case_id` | UUID | FK a `commercial_cases.id`, `RESTRICT`. |
| `stage_id` | UUID | FK a `process_stages.id`, `RESTRICT`. |
| `import_id` | UUID | FK nullable a `event_log_imports.id`; `null` en eventos manuales. |
| `source_row_number` | INTEGER | Fila de origen del CSV; nullable. |
| `event_fingerprint` | VARCHAR(64) | SHA-256 semántico, único y nullable. |
| `activity` | VARCHAR(200) | Obligatorio. |
| `event_type` | ENUM | `STAGE_CHANGE`, `INTERACTION` o `SYSTEM`. |
| `resource` | VARCHAR(150) | Opcional. |
| `timestamp` | TIMESTAMPTZ | Momento del evento, obligatorio e indexado. |
| `metadata` | JSONB | Objeto JSON; `{}` por defecto. |
| `created_at` | TIMESTAMPTZ | Momento de persistencia automático. |

Existe un índice compuesto `(case_id, timestamp)` para recuperar eficientemente el timeline de un caso, además del índice de `timestamp` para la inspección cronológica general.

## `event_log_imports`

Registra cada archivo confirmado mediante el importador del Sprint 2.

| Columna | Tipo | Reglas |
|---|---|---|
| `id` | UUID | Clave primaria. |
| `filename` | VARCHAR(255) | Nombre sanitizado del archivo. |
| `file_sha256` | VARCHAR(64) | SHA-256 único del contenido exacto. |
| `total_rows` | INTEGER | Filas de datos recibidas. |
| `imported_cases` | INTEGER | Casos nuevos creados. |
| `imported_events` | INTEGER | Eventos nuevos persistidos. |
| `skipped_duplicates` | INTEGER | Eventos ya existentes omitidos. |
| `created_at` | TIMESTAMPTZ | Fecha automática de importación e indexada. |

Un mismo archivo no puede confirmarse dos veces. La relación con `events` permite conocer qué importación y fila originó cada evento sin afectar los eventos manuales del Sprint 1.

## Semántica del Event Log

La integración con Process Mining utiliza esta correspondencia desde Sprint 4:

| Event Log | Origen |
|---|---|
| `case:concept:name` | `commercial_cases.case_code` |
| `concept:name` | `process_stages.code` a través de `events.stage_id` |
| descripción original | `events.activity` |
| `time:timestamp` | `events.timestamp` |

Por tanto, el Event Log se apoya en tres conceptos mínimos: **Case ID, Activity y Timestamp**. Este sprint solo garantiza la persistencia compatible; no incluye PM4Py ni algoritmos de minería.

## Transacción de cambio de etapa

Al registrar un evento `STAGE_CHANGE`, el servicio:

1. bloquea y verifica el caso;
2. verifica que la etapa exista y esté activa;
3. agrega el evento;
4. cambia `commercial_cases.current_stage_id`;
5. confirma ambas escrituras en un único `commit`.

Si la escritura falla, se ejecuta `rollback`; el caso conserva su etapa anterior y no queda un evento parcial.

## Operación

```bash
# Aplicar el esquema
docker compose exec backend alembic upgrade head

# Revertir la última revisión
docker compose exec backend alembic downgrade -1

# Restaurar la última revisión
docker compose exec backend alembic upgrade head

# Cargar etapas iniciales
docker compose exec backend python -m scripts.seed_process_stages
```

La revisión inicial del Sprint 1 es `20260919_0001`. La revisión del Sprint 2 es `20260919_0002` y puede revertirse sin eliminar tablas ni datos del Sprint 1.

## `deviations` (Sprint 4)

La revisión `20260920_0003` agrega desviaciones detectadas sin modificar las tablas ni migraciones anteriores. Cada registro referencia el caso y, cuando corresponde, el evento y la etapa. `expected_value`, `actual_value` y `details` son JSONB; `fingerprint` es un SHA-256 único que hace idempotente el análisis. Las claves foráneas usan `RESTRICT` y `resolved_at` queda disponible para un workflow futuro.

## Persistencia ML (Sprint 5)

La revisión `20260920_0004` agrega `ml_model_runs` y `predictions`. La primera conserva historial, métricas, dataset hash, threshold y referencia verificable al artifact; un índice parcial garantiza un único modelo activo. La segunda conserva el snapshot, score, label, nivel, features y explicación asociados a un modelo. Su fingerprint único hace idempotente una inferencia repetida.

Ambas tablas usan claves foráneas `RESTRICT`. El downgrade elimina únicamente estas tablas y el enum de riesgo, sin alterar Event Log ni desviaciones.

## Alertas predictivas (Sprint 6)

La revisión `20260920_0005` agrega `alerts`, `alert_actions`, tres enums y `alert_code_seq`, sin modificar migraciones previas.

`alerts` referencia el caso, la predicción que abrió el ciclo y la predicción evaluada más recientemente. Conserva score y nivel actuales, estado operativo, modo de evaluación, fingerprint SHA-256 y timestamps de atención/cierre. `alert_code` es único y usa una secuencia PostgreSQL; `fingerprint` también es único.

El índice parcial único `uq_alerts_one_open_per_case` sobre `case_id WHERE status IN ('ACTIVE', 'ATTENDED')` impide dos alertas abiertas simultáneas para un caso. Los índices adicionales cubren código, caso, estado, nivel, fecha de generación y predicción más reciente.

`alert_actions` registra `CREATED`, `ATTENDED`, `NOTE`, `RISK_REEVALUATED`, `RESOLVED` y `DISMISSED`. Cada fila conserva actor textual, notas, estado anterior/nuevo, predicción relacionada y detalles JSONB. La creación, reevaluación o transición y su acción se escriben dentro de la misma transacción.

Todas las claves foráneas usan `RESTRICT`. El downgrade de Sprint 6 elimina solamente `alert_actions`, `alerts`, su secuencia y sus enums propios; mantiene intactos `predictions`, `ml_model_runs`, `deviations` y el Event Log.
