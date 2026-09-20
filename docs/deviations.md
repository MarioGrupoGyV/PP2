# Desviaciones y conformidad — Sprint 4

## Fuentes de verdad

El motor lee exclusivamente PostgreSQL. El orden de las etapas activas y su identidad proceden de `process_stages.sequence` y `process_stages.code`; cada SLA procede de `process_stages.sla_hours`. `events.activity` permanece intacto como texto original, pero nunca decide la ruta. El CSV y el ground truth no participan en producción.

## Reglas del MVP

| Tipo | Regla | Severidad |
|---|---|---|
| `STAGE_SKIP` | El siguiente `STAGE_CHANGE` avanza más de una secuencia. | Una omitida: `MEDIUM`; dos o más: `HIGH`. |
| `BACKTRACK` | La secuencia disminuye. | Una posición: `MEDIUM`; dos o más: `HIGH`. |
| `REWORK` | Una etapa canónica vuelve a aparecer en el caso. | Segunda aparición: `MEDIUM`; tercera o posterior: `HIGH`. |
| `SLA_BREACH` | El siguiente cambio ocurre después del SLA de la etapa de origen. | Exceso/SLA ≤ 0,25: `LOW`; ≤ 1: `MEDIUM`; > 1: `HIGH`. |
| `INACTIVITY` | El intervalo entre dos eventos consecutivos supera `DEVIATION_INACTIVITY_HOURS`. | La misma regla proporcional respecto del umbral. |

Las reglas se pueden solapar. Por ejemplo, un mismo cambio puede producir inactividad, SLA excedido y salto de etapa. `STAGE_SKIP`, `BACKTRACK` y `REWORK` son estructurales; `SLA_BREACH` e `INACTIVITY` son temporales.

El análisis es estrictamente histórico: no calcula `now() - último evento`, ni para SLA ni para inactividad. Esto evita resultados dependientes de la fecha de ejecución. Una traza incompleta que sea un prefijo válido sigue siendo estructuralmente conforme.

## Idempotencia y transacción

Cada hallazgo obtiene un SHA-256 determinístico a partir de la versión de regla, caso, tipo, evento actual y evento previo relevante. La restricción única de base de datos impide duplicados. El servicio carga las trazas, calcula los candidatos, consulta fingerprints existentes e inserta los nuevos en una sola transacción; cualquier fallo provoca rollback.

## API e interfaz

- `POST /api/v1/deviations/analyze`
- `GET /api/v1/deviations?type=&severity=&case_code=&page=&page_size=`
- `GET /api/v1/deviations/summary`
- `GET /api/v1/deviations/{id}`
- `GET /api/v1/cases/{id}/deviations`
- `GET /api/v1/cases/{id}/conformance`
- `GET /api/v1/process-mining/expected-model`
- `GET /api/v1/process-mining/conformance`

La vista `/deviations` ofrece ejecución explícita, indicadores, distribución por tipo, filtros, tabla, detalle, conformidad estructural y el camino esperado con sus SLA.

## Fuera de alcance

No se implementan resolución/asignación, vigilancia en tiempo real, Machine Learning, predicciones ni alertas. El ground truth de demostración puede usarse fuera del servicio para evaluar la calidad del detector, pero nunca como entrada de las reglas.
