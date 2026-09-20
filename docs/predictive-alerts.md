# Alertas predictivas — Sprint 6

## Propósito y límites conceptuales

Una **desviación** registra un problema que ya ocurrió, una **predicción** estima riesgo futuro y una **alerta** es el elemento operativo que una persona atiende a partir de una predicción. El módulo de alertas no crea ni modifica eventos o desviaciones y tampoco activa, desactiva o reentrena modelos.

La interfaz y la API usan el término **riesgo estimado**. El score no se presenta como una probabilidad real porque el modelo no tiene una calibración formal demostrada.

## Dos thresholds distintos

- `ml_model_runs.decision_threshold` pertenece al clasificador. Convierte el score en `predicted_label`; el modelo activo actual conserva su valor `0.685`.
- `ALERT_RISK_THRESHOLD` es una regla operativa configurable. Su valor inicial es `0.70` y debe cumplir `0 < valor <= 1`.

Una alerta nueva requiere simultáneamente:

```text
prediction_applicable = true
AND predicted_label = true
AND risk_score >= ALERT_RISK_THRESHOLD
AND caso elegible
AND no existe alerta abierta equivalente
```

El threshold operativo se configura una sola vez en el backend. `ALERT_BATCH_LIMIT` limita a 100 casos cada invocación batch por defecto y admite como máximo 500 mediante configuración.

## Aplicabilidad y momento observable

Si Sprint 5 devuelve `prediction_applicable=false`, por ejemplo `DETERMINISTIC_THRESHOLD_ALREADY_EXCEEDED`, no se crea una alerta predictiva. El batch lo cuenta en `skipped_not_applicable`.

`LATEST_OBSERVATION` evalúa únicamente casos actualmente `ACTIVE` y deja que Sprint 5 construya el snapshot en el último evento almacenado. No sustituye ese instante por `now()`.

`HISTORICAL_REPLAY` aparece solo cuando el cliente proporciona `as_of`. Puede reproducir un caso actualmente cerrado o cancelado si existe un evento observable en ese instante. La construcción de features reutiliza el replay de Sprint 5 y excluye eventos y desviaciones posteriores a `as_of`.

## Ciclo de vida operativo

Estados y transiciones permitidas:

```text
ACTIVE   -> ATTENDED
ACTIVE   -> DISMISSED
ATTENDED -> RESOLVED
ATTENDED -> DISMISSED
```

`RESOLVED` significa que la gestión humana terminó; no significa que el modelo acertó. Una alerta `RESOLVED` o `DISMISSED` no se reabre. Una predicción nueva de alto riesgo, cuyo snapshot sea posterior al cierre, puede iniciar otro ciclo con nuevo código, fingerprint y predicción de origen.

Las transiciones fuera de ese grafo devuelven HTTP `409`. Descartar requiere una nota. Las notas generales pueden agregarse mientras la alerta está abierta.

## Reevaluación

Si ya existe una alerta `ACTIVE` o `ATTENDED`, una predicción aplicable diferente actualiza `latest_prediction_id`, score, nivel, modo y fecha de evaluación. La predicción de origen no cambia. Se registra `RISK_REEVALUATED` con score, nivel e ID de predicción anteriores y nuevos. Una caída bajo `ALERT_RISK_THRESHOLD`, o incluso un label negativo posterior, **no cierra automáticamente** la alerta; la decisión sigue siendo humana.

Repetir exactamente caso, modelo, snapshot y features reutiliza la predicción de Sprint 5. Si el ID de predicción no cambió, el módulo tampoco duplica `RISK_REEVALUATED`.

## Deduplicación y concurrencia

El fingerprint de origen es SHA-256 de JSON canónico con `case_id`, `origin_prediction_id`, `model_version`, `snapshot_timestamp` y `rule_version` (`alert-rule-v1`). `alerts.fingerprint` es único.

El índice parcial único `uq_alerts_one_open_per_case` permite como máximo una fila por `case_id` cuando el estado es `ACTIVE` o `ATTENDED`. Esta defensa en PostgreSQL complementa el bloqueo transaccional y evita flooding aun con evaluaciones concurrentes.

Los códigos legibles se generan con la secuencia PostgreSQL `alert_code_seq` (`ALR-000001`, `ALR-000002`, ...); no dependen de `COUNT(*)` en producción.

## Auditoría (`alert_actions`)

La creación de alerta y su acción `CREATED` se confirman en la misma transacción. Lo mismo ocurre con cada transición y con cada reevaluación. Los tipos son `CREATED`, `ATTENDED`, `NOTE`, `RISK_REEVALUATED`, `RESOLVED` y `DISMISSED`.

`actor` sigue siendo texto opcional porque Sprint 6 no incorpora autenticación ni una tabla de usuarios. `previous_status` y `new_status` dejan explícita cada transición; `details` conserva la trazabilidad de riesgo.

## API

| Método | Ruta | Uso |
|---|---|---|
| `POST` | `/api/v1/cases/{case_id}/alerts/evaluate` | Evaluar un caso, opcionalmente con `as_of`. |
| `POST` | `/api/v1/alerts/evaluate` | Evaluar hasta `limit` casos; admite `case_id`, `case_ids` y `as_of`. |
| `GET` | `/api/v1/alerts` | Listar por estado, nivel, caso y score mínimo. |
| `GET` | `/api/v1/alerts/summary` | Totales por estado y riesgo medio abierto. |
| `GET` | `/api/v1/alerts/{id}` | Detalle, predicciones y factores actuales. |
| `GET` | `/api/v1/cases/{case_id}/alerts` | Historial cronológico del caso. |
| `GET` | `/api/v1/alerts/{id}/actions` | Timeline auditable. |
| `POST` | `/api/v1/alerts/{id}/actions` | Agregar una nota. |
| `POST` | `/api/v1/alerts/{id}/attend` | `ACTIVE -> ATTENDED`. |
| `POST` | `/api/v1/alerts/{id}/resolve` | `ATTENDED -> RESOLVED`. |
| `POST` | `/api/v1/alerts/{id}/dismiss` | Descartar con justificación. |

El resultado batch diferencia predicciones creadas/reutilizadas, alertas creadas/actualizadas, casos bajo threshold, no aplicables, inelegibles y sin estado observable.

## Interfaz y limitaciones

`/alerts` incluye cards, evaluación explícita, reproducción histórica, bandeja priorizada, filtros, detalle, factores, timeline y acciones válidas. `/predictions` enlaza a la alerta abierta cuando existe.

- No hay scheduler, workers, streaming ni ejecución al iniciar FastAPI.
- No hay notificaciones externas.
- No hay autenticación, roles, usuarios, agentes, LLM ni RAG.
- El cierre es una decisión humana y no mide exactitud predictiva.
- Un nuevo ciclo exige un snapshot posterior al cierre operacional anterior.
