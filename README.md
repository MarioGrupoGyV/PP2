# Sistema de minería de procesos con alertas predictivas para detectar desviaciones en la gestión comercial inmobiliaria

Base técnica para un sistema que, en futuros sprints, permitirá analizar el proceso comercial inmobiliario y detectar desviaciones. El Sprint 0 implementa únicamente la comunicación **Frontend → Backend → PostgreSQL** y no incluye lógica comercial, minería de procesos, Machine Learning ni autenticación.

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
│   │   ├── models/           # Modelos futuros
│   │   ├── repositories/     # Acceso a datos futuro
│   │   ├── schemas/          # Esquemas Pydantic
│   │   └── services/         # Casos de uso futuros
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── database/                 # Recursos de base de datos futuros
├── docs/                     # Documentación futura
├── scripts/                  # Automatizaciones futuras
├── .env.example
└── docker-compose.yml
```

La API queda preparada para incorporar routers bajo `/api/v1` para `cases`, `events`, `process-mining`, `deviations`, `predictions`, `alerts` y `dashboard`, pero ninguno se implementa en este sprint.

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

## Pendiente para Sprint 1

El siguiente sprint podrá definir el modelo de datos comercial y el Event Log, sus migraciones y los primeros endpoints funcionales. Siguen fuera de este Sprint 0 la autenticación, los casos comerciales, la importación de archivos, la minería de procesos, PM4Py, Machine Learning, predicciones, alertas, IA, integraciones externas y el dashboard funcional.
