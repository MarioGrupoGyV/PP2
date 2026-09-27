# Sprint 8 — Analista IA local

## Objetivo y costo

El Analista IA consulta y explica información ya existente en el sistema G&V. El módulo utiliza un modelo ejecutado localmente mediante Ollama y no requiere una API de inferencia pagada. Por tanto, funciona **sin costo por llamada a API**; el equipo local sí consume memoria, CPU o GPU y electricidad.

Los datos de este repositorio son simulados para demostración y no representan resultados comerciales reales de G&V.

## Arquitectura

```text
React /analyst
      │ REST/JSON
      ▼
FastAPI /api/v1/analyst
      │
      ▼
ProcessAnalystAgent ──► Ollama ──► modelo local configurable
      │                    │
      │      tool call validado
      ▼                    │
ToolRegistry → Pydantic → ToolExecutor
      │
      ▼
Servicios y repositorios determinísticos existentes → PostgreSQL
```

El navegador solo se comunica con FastAPI. El modelo no recibe acceso a PostgreSQL, SQL, shell, Internet ni endpoints internos. Tampoco se usan embeddings, una base vectorial o RAG.

Existe un solo agente, `ProcessAnalystAgent`. Su ciclo envía la pregunta y los esquemas de herramientas a Ollama; valida cada llamada, ejecuta la función de lectura y devuelve el resultado al modelo hasta obtener una respuesta final. El límite predeterminado es de seis rondas.

## Herramientas de solo lectura

| Herramienta | Fuente determinística |
|---|---|
| `get_case` | Servicio de casos |
| `get_case_timeline` | Servicio de eventos |
| `get_case_conformance` | Servicio de conformidad |
| `get_case_deviations` | Servicio de desviaciones |
| `get_case_prediction` | Predicción persistida más reciente |
| `get_case_alerts` | Servicio de alertas |
| `get_process_summary` | Process Mining |
| `get_process_variants` | Process Mining |
| `get_process_transitions` | Process Mining |
| `get_deviation_summary` | Servicio de desviaciones |
| `get_alert_summary` | Servicio de alertas |

No se exponen operaciones para crear predicciones, analizar desviaciones, evaluar o cambiar alertas, importar datos, modificar etapas o entrenar modelos. El agente no calcula valores críticos: `risk_score`, SLA, conformidad, desviaciones, frecuencias y umbrales provienen de los servicios existentes.

Cada entrada se valida con un modelo Pydantic estricto. Un nombre desconocido, JSON mal formado, un campo adicional o ausente produce un resultado controlado y nunca una ejecución parcial. Si ninguna herramienta solicitada termina correctamente, la respuesta factual del modelo se descarta y la API responde: «No pude consultar la información solicitada.»

Cuando la pregunta menciona un único código de caso, el backend comprueba que el `case_code` solicitado por la tool coincida antes de ejecutar la consulta. Si no coincide, devuelve un error de argumentos al modelo para permitir un reintento dentro del límite de rondas; nunca sustituye el código ni ejecuta una tool adicional por su cuenta. Si el registro no existe, la respuesta final comunica que no se encontró en vez de aceptar una afirmación factual del modelo.

`evidence` se construye en el backend a partir de herramientas realmente ejecutadas; nunca lo redacta el LLM. La respuesta pública expone nombres, estados, tiempos y rondas, pero no razonamiento interno.

## Configuración

```dotenv
ANALYST_ENABLED=true
ANALYST_LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=qwen2.5:7b
ANALYST_MAX_TOOL_ROUNDS=6
ANALYST_MAX_HISTORY_MESSAGES=10
ANALYST_TIMEOUT_SECONDS=60
ANALYST_MAX_TOOL_RESULT_ITEMS=50
ANALYST_TEMPERATURE=0.1
```

`OLLAMA_MODEL` es la única selección del modelo. Puede cambiarse por cualquier modelo de Ollama compatible con tool calling. `qwen2.5:7b` es la opción recomendada y su descarga ronda los 4.7 GB. Para un equipo con menos memoria puede evaluarse un modelo compatible cercano a 3B; los modelos 7B/8B suelen responder mejor, pero requieren más RAM. No se exige CUDA ni GPU dedicada: Ollama puede inferir por CPU, con mayor latencia.

En la laptop usada para validar este Sprint, Docker/WSL disponía de unos 3.5 GiB de RAM. El modelo `qwen2.5:7b` se descargó, pero no llegó a responder dentro de 60 segundos al intentar cargarlo con ese límite. Se probó `qwen2.5:3b` (descarga aproximada de 1.9 GB; unos 2.2 GiB de RAM observados en Ollama) con esta configuración local, sin cambiar los valores predeterminados del repositorio:

```dotenv
OLLAMA_MODEL=qwen2.5:3b
ANALYST_TIMEOUT_SECONDS=180
```

Escribe esas dos líneas en un `.env` local y ejecuta `docker compose exec ollama ollama pull qwen2.5:3b` una sola vez antes de la exposición. `.env` no se versiona. En una máquina con memoria suficiente, conserva el modelo 7B predeterminado.

El backend arranca y los módulos previos continúan operativos si Ollama está apagado, el modelo falta o `ANALYST_ENABLED=false`. Solo `/analyst` se muestra no disponible.

## Instalación con Ollama en Docker

El volumen `ollama_data` evita descargar el modelo en cada reconstrucción. El pull es un paso de infraestructura explícito y FastAPI nunca lo ejecuta.

```bash
docker compose pull ollama
docker compose up -d database ollama
docker compose exec ollama ollama pull qwen2.5:7b
docker compose up -d --build backend frontend
```

Para sustituir el modelo, define `OLLAMA_MODEL` en `.env` y ejecuta una sola vez el `ollama pull` correspondiente.

## Alternativa: Ollama instalado en Windows

1. Instala Ollama en el host.
2. Ejecuta `ollama pull qwen2.5:7b` una sola vez.
3. Si FastAPI está en Docker, configura:

```dotenv
OLLAMA_BASE_URL=http://host.docker.internal:11434
```

Si FastAPI se ejecuta también en el host, usa `http://localhost:11434`. El código no está acoplado a ninguna de las dos ubicaciones.

## Endpoints

```text
GET  /api/v1/analyst/status
POST /api/v1/analyst/chat
```

Ejemplo de consulta:

```bash
curl http://localhost:8000/api/v1/analyst/status

curl -X POST http://localhost:8000/api/v1/analyst/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"¿Cuál es la variante más frecuente?","history":[],"context_case_code":null}'
```

El historial aceptado contiene únicamente mensajes `user` y `assistant`, se conserva en la memoria del navegador y no se persiste. Desde el detalle de un caso, «Preguntar al Analista» abre `/analyst?case=...`; el código funciona como contexto auxiliar, nunca como sustituto de una herramienta.

## Preparación de una demostración offline

Realiza estos pasos mientras haya Internet, no durante la exposición:

1. Instala Docker Desktop y/o Ollama.
2. Descarga una vez la imagen de Ollama y el modelo con los comandos anteriores.
3. Verifica `docker compose exec ollama ollama list`.
4. Levanta los servicios con `docker compose up -d --build`.
5. Comprueba que `/api/v1/analyst/status` devuelve `available: true`.
6. Desconecta Internet, abre `http://localhost:5173/analyst` y ejecuta las preguntas preparadas.

Preguntas sugeridas:

- ¿Cuál es la variante más frecuente?
- ¿Qué transición tiene mayor duración?
- ¿Cuántos casos tienen retrabajo?
- ¿Qué desviaciones tiene DEMO-00089?
- ¿Por qué DEMO-00141 tiene riesgo alto?
- ¿Cuál es el estado de la alerta de DEMO-00141?

El script opcional `python backend/scripts/test_analyst_local.py` comprueba una instalación real mediante la API. Usa `--all` para ejecutar las seis preguntas y resumir respuestas, tools y tiempos. No forma parte de `pytest`, por lo que las pruebas automatizadas funcionan offline con `FakeLLMClient`.

## Seguridad y limitaciones

- La precisión lingüística y el uso correcto de herramientas dependen del modelo local elegido.
- La inferencia por CPU puede tardar varios segundos o más; la API informa tiempo total y rondas.
- En equipos con disco o CPU lentos, la primera carga puede superar 60 segundos. Precalienta el modelo antes de la exposición con `docker compose exec ollama ollama run <modelo> "Responde OK"` o aumenta `ANALYST_TIMEOUT_SECONDS` de forma explícita.
- El LLM explica resultados, pero no convierte el score en una probabilidad calibrada. Usa «riesgo estimado» y «factor asociado», no «causa».
- El contexto conversacional está limitado y no se almacena.
- El sistema no ofrece garantías absolutas de privacidad: la configuración de red y del equipo sigue siendo responsabilidad del operador.
- El módulo es de consulta; no reemplaza la revisión humana ni ejecuta decisiones operativas.

## Verificación

```bash
python -m pytest backend/tests
cd frontend && npm run build
docker compose config --quiet
docker compose exec backend alembic check
docker compose exec backend python -m scripts.check_data_integrity
```

El baseline protegido del Sprint 8 está en `docs/integrity-sprint8-baseline.json`.
