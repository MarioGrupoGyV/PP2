# Sistema de minería de procesos con alertas predictivas para detectar desviaciones en la gestión comercial inmobiliaria

Sistema en evolución para representar, descubrir y contrastar el proceso comercial inmobiliario desde un Event Log. Los Sprints 0–4 implementaron infraestructura, persistencia, importación trazable, Process Mining y detección histórica de desviaciones; el Sprint 5 incorpora la estimación ML de riesgo `NEXT_DEVIATION`. Todavía no incluye alertas ni autenticación.

## Arquitectura

El proyecto es un monorepo modular con tres servicios desplegables mediante Docker Compose:

```text
Navegador
   │ HTTP
   ▼
React + TypeScript + Vite (puerto 5173)
   │ REST/JSON
   ▼
FastAPI + SQLAlchemy (puerto 8000)
   │ SQL
   ▼
PostgreSQL (puerto 5432)
```

Se usa una única aplicación backend; no hay microservicios. PostgreSQL mantiene sus datos en un volumen de Docker.

## Stack

- Frontend: React, TypeScript, Vite y Tailwind CSS.
- Backend: Python, FastAPI, Pydantic y SQLAlchemy.
- Base de datos: PostgreSQL con el driver Psycopg.
- Infraestructura: Docker y Docker Compose.
- Control de versiones: Git.

## Estructura principal

```text
.
├── frontend/
│   ├── src/
│   │   ├── app/              # Composición de la aplicación
│   │   ├── components/       # Componentes visuales
│   │   ├── hooks/            # Estado de infraestructura
│   │   ├── services/         # Cliente HTTP centralizado
│   │   └── types/            # Contratos TypeScript
│   ├── Dockerfile
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── api/routes/       # Routers HTTP
│   │   ├── core/             # Configuración y base de datos
│   │   ├── models/           # Entidades del dominio comercial
│   │   ├── repositories/     # Consultas y persistencia
│   │   ├── schemas/          # Esquemas Pydantic
│   │   └── services/         # Reglas y transacciones
│   ├── alembic/              # Migraciones de base de datos
│   ├── scripts/              # Seeds operativos
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── database/                 # Recursos de base de datos futuros
├── docs/                     # Documentación futura
├── scripts/                  # Automatizaciones futuras
├── .env.example
└── docker-compose.yml
```

La API usa routers separados bajo `/api/v1`. Process Mining, desviaciones y predicción de riesgo están implementados; alertas y notificaciones permanecen pendientes.

## Requisitos

La opción recomendada requiere:

- Docker Desktop o Docker Engine con Docker Compose.
- Git.

Para ejecución local sin Docker también se requiere Node.js 20 o superior, npm y Python 3.11 o superior, además de una instancia accesible de PostgreSQL.

## Configuración del entorno

1. Copia `.env.example` como `.env`.
2. Cambia `POSTGRES_PASSWORD` si el entorno no es exclusivamente local.
3. Conserva `POSTGRES_HOST=database` cuando ejecutes todo con Docker Compose.
4. `VITE_API_URL` debe ser una URL accesible desde el navegador, normalmente `http://localhost:8000`.

PowerShell:

```powershell
Copy-Item .env.example .env
```

Bash:

```bash
cp .env.example .env
```

`.env` está excluido de Git; `.env.example` contiene solo valores de desarrollo y sí debe versionarse.

## Ejecución con Docker

Desde la raíz del repositorio:

```bash
docker compose up --build
```

Para detener los servicios sin eliminar los datos:

```bash
docker compose down
```

Para eliminar también el volumen local de PostgreSQL (esto borra sus datos):

```bash
docker compose down --volumes
```

## Ejecución local sin Docker

### PostgreSQL

Puedes iniciar solo la base de datos:

```bash
docker compose up -d database
```

Para que el backend ejecutado fuera de Docker acceda a ella, configura en `.env` `POSTGRES_HOST=localhost` y elimina o ajusta `DATABASE_URL` para que use `localhost`.

### Backend

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements-dev.txt
uvicorn app.main:app --reload --app-dir backend --host 0.0.0.0 --port 8000
```

Bash:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r backend/requirements-dev.txt
uvicorn app.main:app --reload --app-dir backend --host 0.0.0.0 --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

## URLs de desarrollo

| Recurso | URL |
|---|---|
| Página técnica | http://localhost:5173 |
| API | http://localhost:8000 |
| Swagger UI | http://localhost:8000/docs |
| OpenAPI | http://localhost:8000/openapi.json |
| PostgreSQL | localhost:5432 |

## Endpoints del Sprint 0

| Método | Ruta | Propósito |
|---|---|---|
| `GET` | `/api/v1/health` | Comprueba que FastAPI responde. |
| `GET` | `/api/v1/health/database` | Ejecuta `SELECT 1` para comprobar PostgreSQL. |

Respuesta del backend:

```json
{
  "status": "ok",
  "service": "backend"
}
```

Respuesta de base de datos conectada:

```json
{
  "status": "ok",
  "database": "connected"
}
```

Si PostgreSQL no está disponible, el segundo endpoint responde `503 Service Unavailable` con un mensaje genérico que no expone credenciales.

## Pruebas y verificaciones

```bash
# Backend
python -m pytest backend/tests

# Frontend
cd frontend
npm run build

# Configuración de contenedores
docker compose config
```

## Alcance del Sprint 0

- Estructura modular del monorepo.
- Aplicación React de comprobación con estados de carga, éxito y error.
- API FastAPI con configuración centralizada, CORS y sesiones SQLAlchemy.
- Conectividad real con PostgreSQL mediante `SELECT 1`.
- Dockerfiles, red interna, health checks y persistencia de PostgreSQL.
- Variables de entorno de ejemplo, pruebas básicas y documentación.

No se crean tablas ni datos simulados en este sprint.

## Sprint 1 — Modelo de datos y Event Log

Sprint 1 agrega el dominio mínimo para persistir recorridos comerciales. La especificación detallada se encuentra en [`docs/database.md`](docs/database.md).

### Tablas

- `process_stages`: catálogo configurable y ordenado de etapas con SLA.
- `commercial_cases`: instancia de un proceso comercial y su etapa actual.
- `events`: actividades cronológicas que forman el Event Log.

Las claves primarias son UUID. Las relaciones usan claves foráneas con `RESTRICT`; no existen endpoints de borrado físico. `events.metadata` usa JSONB en PostgreSQL.

### Migraciones

El backend ejecuta `alembic upgrade head` automáticamente antes de iniciar Uvicorn en Docker. También puede operarse manualmente:

```bash
docker compose exec backend alembic current
docker compose exec backend alembic upgrade head
docker compose exec backend alembic downgrade -1
```

Para ejecutar Alembic localmente desde la raíz, con el entorno virtual activo y PostgreSQL disponible:

```bash
alembic -c backend/alembic.ini upgrade head
alembic -c backend/alembic.ini downgrade -1
```

No se usa `Base.metadata.create_all()` en la aplicación; Alembic es la única vía de creación del esquema productivo.

### Seed de etapas

Con los contenedores activos:

```bash
docker compose exec backend python -m scripts.seed_process_stages
```

El seed crea `LEAD`, `CONTACTED`, `QUALIFIED`, `VISIT`, `RESERVED` y `CONTRACT`. Es idempotente: una segunda ejecución no duplica ni sobrescribe etapas existentes.

### Endpoints del Sprint 1

| Método | Ruta | Propósito |
|---|---|---|
| `GET` | `/api/v1/process-stages` | Listar etapas por secuencia. |
| `GET` | `/api/v1/process-stages/{id}` | Obtener una etapa. |
| `POST` | `/api/v1/process-stages` | Crear una etapa. |
| `PATCH` | `/api/v1/process-stages/{id}` | Editar o desactivar una etapa. |
| `GET` | `/api/v1/cases` | Listar casos con paginación. |
| `POST` | `/api/v1/cases` | Crear un caso. |
| `GET` | `/api/v1/cases/{id}` | Obtener un caso por UUID. |
| `GET` | `/api/v1/cases/code/{case_code}` | Obtener un caso por código. |
| `POST` | `/api/v1/cases/{case_id}/events` | Registrar un evento. |
| `GET` | `/api/v1/cases/{case_id}/events` | Obtener el timeline cronológico. |
| `GET` | `/api/v1/events` | Inspeccionar el Event Log paginado. |

Los listados paginados aceptan `page` y `page_size`. Los errores de recurso inexistente, conflictos de unicidad y validación responden `404`, `409` y `422`, respectivamente.

### Ejemplo básico

Después de ejecutar el seed, obtén los UUID de las etapas con:

```bash
curl http://localhost:8000/api/v1/process-stages
```

Crea un caso usando el UUID de `LEAD`:

```bash
curl -X POST http://localhost:8000/api/v1/cases \
  -H "Content-Type: application/json" \
  -d '{
    "case_code": "CASE-001",
    "current_stage_id": "<LEAD_UUID>",
    "assigned_resource": "Asesor 01",
    "source": "META_ADS",
    "status": "ACTIVE",
    "started_at": "2026-09-19T09:00:00Z"
  }'
```

Registra actividades sustituyendo los UUID correspondientes:

```bash
curl -X POST http://localhost:8000/api/v1/cases/<CASE_UUID>/events \
  -H "Content-Type: application/json" \
  -d '{
    "stage_id": "<CONTACTED_UUID>",
    "activity": "Contactado",
    "event_type": "STAGE_CHANGE",
    "resource": "Asesor 01",
    "timestamp": "2026-09-19T10:00:00Z",
    "metadata": {"channel": "whatsapp", "result": "answered"}
  }'
```

Cada `STAGE_CHANGE` crea el evento y actualiza `current_stage_id` dentro de la misma transacción.

### Pruebas

```bash
python -m pytest backend/tests -v
```

Las pruebas usan una base SQLite aislada únicamente como doble de prueba. Las migraciones y verificaciones finales se ejecutan además contra PostgreSQL 17.

## Sprint 2 — Importación y preparación del Event Log

Sprint 2 incorpora un pipeline transaccional **CSV → validación → normalización → preview → confirmación → persistencia**. La especificación detallada se encuentra en [`docs/event-log-import.md`](docs/event-log-import.md).

### Formato CSV

Columnas obligatorias:

- `case_code`
- `stage_code`
- `activity`
- `timestamp`

Columnas opcionales: `resource`, `event_type`, `source` y `metadata`. `event_type` usa `STAGE_CHANGE` por defecto y `metadata` usa `{}`. El límite por archivo es 10 MB y el encoding debe ser UTF-8 o UTF-8-SIG.

### Endpoints del Sprint 2

| Método | Ruta | Propósito |
|---|---|---|
| `POST` | `/api/v1/imports/preview` | Validar un CSV sin persistir datos. |
| `POST` | `/api/v1/imports/commit` | Revalidar e importar atómicamente. |
| `GET` | `/api/v1/imports` | Listar importaciones recientes. |
| `GET` | `/api/v1/imports/{id}` | Consultar una importación. |
| `GET` | `/api/v1/imports/template` | Descargar un CSV de ejemplo. |
| `GET` | `/api/v1/event-log` | Obtener el Event Log normalizado. |

La interfaz está disponible en http://localhost:5173/imports.

### Preview e importación

```bash
curl -X POST http://localhost:8000/api/v1/imports/preview \
  -F "file=@data/demo_event_log.csv"

curl -X POST http://localhost:8000/api/v1/imports/commit \
  -F "file=@data/demo_event_log.csv"
```

El commit solo se permite cuando todas las filas son válidas. El backend vuelve a validar el archivo, aunque ya exista un preview exitoso.

### Deduplicación y trazabilidad

- `file_sha256` identifica el contenido exacto del archivo; repetirlo responde `409`.
- Cada fila normalizada obtiene un fingerprint SHA-256 basado en caso, etapa, actividad, timestamp UTC, tipo, recurso, fuente y metadata JSON canónica.
- El índice único de `event_fingerprint` evita repetir eventos entre archivos diferentes.
- `events.import_id` y `events.source_row_number` conservan la procedencia.
- Los eventos manuales mantienen estos campos y el fingerprint en `null`.

### Generador de datos ficticios

```bash
python backend/scripts/generate_demo_event_log.py \
  --cases 400 \
  --seed 42 \
  --output data/demo_event_log.csv
```

El comando también genera `data/demo_event_log_ground_truth.csv`. El Event Log principal no contiene el escenario; el ground truth se mantiene separado para evaluación futura. Con el mismo seed se obtiene exactamente el mismo dataset.

Distribución configurada:

- `NORMAL`: 55 %
- `STAGE_SKIP`: 10 %
- `REWORK`: 10 %
- `BACKTRACK`: 10 %
- `LONG_DELAY`: 15 %

Los archivos en `data/` están ignorados por Git.

## Sprint 3 — Minería de Procesos

Sprint 3 analiza bajo demanda los eventos `STAGE_CHANGE` almacenados en PostgreSQL. La integración usa PM4Py `2.7.23.8` y está encapsulada en el servicio de Process Mining; no lee los CSV originales ni utiliza el ground truth del generador. La explicación completa está en [`docs/process-mining.md`](docs/process-mining.md).

### Transformación y descubrimiento

| PostgreSQL | PM4Py |
|---|---|
| `commercial_cases.case_code` | `case:concept:name` |
| `process_stages.code` | `concept:name` |
| `events.timestamp` | `time:timestamp` |
| `events.resource` | `org:resource` |

La consulta se ordena por caso y timestamp, normaliza el tiempo a UTC y entrega un DataFrame a `pm4py.discover_dfg`. El DFG, las actividades iniciales/finales y las variantes se descubren desde los datos. Pandas se usa para enriquecer las transiciones con frecuencia por caso y duraciones promedio, mediana, mínima y máxima.

### Endpoints del Sprint 3

| Método | Ruta | Propósito |
|---|---|---|
| `GET` | `/api/v1/process-mining/dfg` | Nodos, conexiones e inicios/finales observados. |
| `GET` | `/api/v1/process-mining/performance` | Duraciones de las transiciones. |
| `GET` | `/api/v1/process-mining/variants?limit=20` | Variantes ordenadas por cantidad de casos. |
| `GET` | `/api/v1/process-mining/variants/{variant_id}/cases` | Casos paginados de una variante. |
| `GET` | `/api/v1/process-mining/summary` | Métricas generales del Event Log analizado. |
| `GET` | `/api/v1/process-mining/activities` | Frecuencia total y por caso de cada actividad. |
| `GET` | `/api/v1/process-mining/transitions` | Frecuencia, porcentaje y tiempos por transición. |

La interfaz está disponible en http://localhost:5173/process-mining. Incluye indicadores, mapa React Flow con layout Dagre, detalle de nodos y conexiones, variantes con casos asociados y tabla de transiciones.

```bash
curl http://localhost:8000/api/v1/process-mining/summary
curl http://localhost:8000/api/v1/process-mining/dfg
curl "http://localhost:8000/api/v1/process-mining/variants?limit=20"
```

PM4Py Community Edition se distribuye bajo AGPL-3.0-or-later. Antes de un despliegue comercial cerrado debe revisarse la compatibilidad de licencia o adquirirse la licencia correspondiente del proveedor.

## Sprint 4 — Desviaciones y conformidad

Sprint 4 compara los eventos persistidos con las etapas activas configuradas en `process_stages`. La identidad canónica usada por Process Mining es `process_stages.code`; `events.activity` se conserva como descripción original. Las reglas, contratos y decisiones se documentan en [`docs/deviations.md`](docs/deviations.md).

| Método | Ruta | Propósito |
|---|---|---|
| `POST` | `/api/v1/deviations/analyze` | Ejecutar las cinco reglas de forma idempotente. |
| `GET` | `/api/v1/deviations` | Listar y filtrar desviaciones. |
| `GET` | `/api/v1/deviations/summary` | Resumir casos, tipos y severidades. |
| `GET` | `/api/v1/deviations/{id}` | Consultar el detalle. |
| `GET` | `/api/v1/cases/{id}/deviations` | Obtener el timeline de desviaciones de un caso. |
| `GET` | `/api/v1/cases/{id}/conformance` | Consultar conformidad estructural y temporal. |
| `GET` | `/api/v1/process-mining/expected-model` | Obtener etapas y SLA esperados. |
| `GET` | `/api/v1/process-mining/conformance` | Obtener el resumen global de conformidad. |

La interfaz se encuentra en http://localhost:5173/deviations. El umbral histórico de inactividad se configura mediante `DEVIATION_INACTIVITY_HOURS` (72 horas por defecto).

Permanecen fuera de alcance las alertas en tiempo real y los workflows de resolución.

## Sprint 5 — Predicción de riesgo

Sprint 5 construye snapshots históricos sin leakage y estima si ocurrirá una desviación en la ventana `(snapshot, siguiente STAGE_CHANGE]`. El diseño, features, split, modelos y limitaciones se explican en [`docs/predictive-model.md`](docs/predictive-model.md).

| Método | Ruta | Propósito |
|---|---|---|
| `POST` | `/api/v1/cases/{id}/predict` | Calcular o reutilizar el riesgo para un snapshot. |
| `GET` | `/api/v1/cases/{id}/prediction` | Obtener la predicción más reciente del caso. |
| `GET` | `/api/v1/predictions` | Listar predicciones persistidas. |
| `GET` | `/api/v1/ml/model` | Consultar el modelo activo. |
| `GET` | `/api/v1/ml/evaluation` | Consultar evaluación persistida. |

La interfaz está disponible en http://localhost:5173/predictions. El entrenamiento es explícito y nunca se ejecuta al iniciar FastAPI:

```bash
docker compose exec backend python -m scripts.train_predictive_model
```

Sprint 4 informa “el caso superó el SLA”; Sprint 5 informa “el caso presenta un riesgo estimado de desviación antes de su próxima transición”. No se generan alertas automáticamente.

## Sprint 6 — Alertas predictivas operativas

Sprint 6 convierte predicciones elegibles de alto riesgo en elementos de trabajo auditables sin modificar el modelo activo. Las reglas se documentan en [`docs/predictive-alerts.md`](docs/predictive-alerts.md).

| Método | Ruta | Propósito |
|---|---|---|
| `POST` | `/api/v1/cases/{id}/alerts/evaluate` | Evaluar una alerta para un caso y snapshot. |
| `POST` | `/api/v1/alerts/evaluate` | Ejecutar evaluación batch explícita y acotada. |
| `GET` | `/api/v1/alerts` | Consultar la bandeja priorizada. |
| `GET` | `/api/v1/alerts/summary` | Obtener indicadores operativos. |
| `GET` | `/api/v1/alerts/{id}` | Ver riesgo, predicciones y factores. |
| `GET/POST` | `/api/v1/alerts/{id}/actions` | Consultar la auditoría o agregar una nota. |
| `POST` | `/api/v1/alerts/{id}/attend` | Registrar atención. |
| `POST` | `/api/v1/alerts/{id}/resolve` | Resolver una alerta atendida. |
| `POST` | `/api/v1/alerts/{id}/dismiss` | Descartar justificadamente. |

La interfaz está disponible en http://localhost:5173/alerts. `ALERT_RISK_THRESHOLD=0.70` es independiente del `decision_threshold` del modelo; ambos deben cumplirse para originar una alerta. No existe evaluación automática, notificación externa, autenticación ni agente en este sprint.
