# Sistema de minería de procesos con alertas predictivas para detectar desviaciones en la gestión comercial inmobiliaria

Sistema en evolución para representar el proceso comercial inmobiliario como un Event Log. El Sprint 0 implementó la comunicación **Frontend → Backend → PostgreSQL** y el Sprint 1 incorpora etapas configurables, casos comerciales y eventos persistentes. Todavía no incluye minería de procesos, Machine Learning ni autenticación.

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

La API usa routers separados bajo `/api/v1`. Los módulos de Process Mining, desviaciones, predicciones, alertas y dashboard permanecen pendientes.

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

## Pendiente para Sprint 2

Permanecen fuera de alcance Process Mining, PM4Py, análisis de desviaciones, reglas automáticas de SLA, Machine Learning, predicciones, alertas, autenticación, usuarios, integraciones externas y dashboard funcional.
