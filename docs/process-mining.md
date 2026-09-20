# Minería de Procesos — Sprint 3

Sprint 3 descubre el proceso comercial realmente observado sin compararlo todavía con un modelo esperado.

```text
PostgreSQL: commercial_cases + events
  → filtro event_type = STAGE_CHANGE
  → DataFrame PM4Py ordenado por caso y timestamp
  → Directly-Follows Graph
  → variantes y métricas temporales
  → API JSON
  → React Flow
```

## Fuente de datos

PostgreSQL es la única fuente del análisis. Los CSV y el archivo ground truth del generador no se leen desde el servicio productivo. La consulta recupera todos los eventos requeridos de una vez y excluye `INTERACTION` y `SYSTEM`, porque el flujo principal representa cambios de etapa.

La correspondencia con PM4Py es:

| Columna PM4Py | Origen |
|---|---|
| `case:concept:name` | `commercial_cases.case_code` |
| `concept:name` | `process_stages.code` |
| `activity:label` | `process_stages.name` |
| `event:original_activity` | `events.activity` |
| `time:timestamp` | `events.timestamp`, normalizado a UTC |
| `org:resource` | `events.resource` |

La transformación mantiene columnas auxiliares internas para relacionar cada variante con sus casos, pero no modifica eventos ni casos persistidos. El código de etapa es la identidad estable: dos textos originales distintos asociados a la misma etapa forman una única actividad canónica.

## Descubrimiento

PM4Py `2.7.23.8` ejecuta `discover_dfg` para obtener:

- transiciones directamente sucesivas y su frecuencia;
- actividades iniciales;
- actividades finales.

`get_variants_as_tuples` obtiene las secuencias distintas. Cada `variant_id` son los primeros 16 caracteres del SHA-256 de la secuencia separada canónicamente, por lo que permanece estable mientras no cambie la ruta.

No se codifica un flujo comercial esperado. Una conexión se conserva aunque retroceda o salte etapas, siempre que exista en los eventos.

## Métricas

El servicio calcula en memoria:

- frecuencia de cada actividad y cantidad de casos distintos;
- frecuencia de cada transición y cantidad de casos distintos;
- porcentaje de una transición respecto del total de salidas de su actividad de origen;
- duración promedio, mediana, mínima y máxima de cada transición;
- número de casos, eventos, actividades y variantes;
- duración promedio y mediana de los casos.

La duración de un caso es la diferencia entre su último y primer `STAGE_CHANGE`. Un caso con un único evento tiene duración cero y continúa formando parte de los conteos.

Los tiempos describen lo observado. No se interpretan como reglas de SLA.

## API

- `GET /api/v1/process-mining/dfg`
- `GET /api/v1/process-mining/performance`
- `GET /api/v1/process-mining/variants?limit=20`
- `GET /api/v1/process-mining/variants/{variant_id}/cases?page=1&page_size=20`
- `GET /api/v1/process-mining/summary`
- `GET /api/v1/process-mining/activities`
- `GET /api/v1/process-mining/transitions`
- `GET /api/v1/process-mining/expected-model`
- `GET /api/v1/process-mining/conformance`

Las respuestas son contratos Pydantic simples y no exponen objetos internos de PM4Py. Cuando el Event Log está vacío, los endpoints generales devuelven colecciones y métricas vacías; consultar una variante inexistente responde `404`.

## Frontend

`/process-mining` incluye:

- indicadores del análisis;
- DFG interactivo con React Flow;
- layout jerárquico izquierda a derecha mediante Dagre;
- detalle de actividad y transición al seleccionar el mapa;
- tabla de variantes y consulta de casos asociados;
- tabla de transiciones y tiempos legibles;
- estados de carga, respuesta vacía y fallo controlado.

La interfaz utiliza lenguaje neutral como “transición observada”, “ruta” y “variante”.

## Operación

```bash
python -m pytest backend/tests
cd frontend && npm run build
docker compose up --build -d
docker compose exec backend python -c "import pm4py; print(pm4py.__version__)"
docker compose exec backend alembic check
```

No se agregó ninguna tabla ni migración en Sprint 3. Los resultados se recalculan bajo demanda y no existe caché.

## Licencia

PM4Py Community Edition `2.7.23.8` se distribuye bajo AGPL-3.0-or-later. Si el sistema se distribuye o presta como servicio sin abrir el código correspondiente, debe evaluarse la licencia comercial ofrecida por el proveedor.

Desde Sprint 4, el modelo esperado y la conformidad se exponen por endpoints separados y se documentan en `deviations.md`. PM4Py continúa describiendo el proceso observado; las reglas no dependen de los CSV ni del ground truth.
