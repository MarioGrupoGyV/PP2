# Integración de interfaz — Sprint 7

Sprint 7 convierte los módulos construidos en los sprints anteriores en una aplicación interna coherente para G&V. La integración reutiliza los contratos REST existentes y no cambia el Event Log, las desviaciones persistidas, el modelo activo, los thresholds ni las reglas analíticas.

## 1. App Shell

`AppShell` establece la estructura permanente de la aplicación: Sidebar a la izquierda en escritorio, Topbar superior y área principal sobre un fondo neutro. En pantallas pequeñas la navegación se oculta y se abre como panel superpuesto mediante el botón de menú. El contenido de cada módulo conserva su lógica previa dentro de este marco compartido.

## 2. Navegación

La navegación definitiva incluye Dashboard, Casos, Minería de Procesos, Desviaciones, Predicciones, Alertas e Importaciones. Las rutas y su estado activo se declaran una sola vez en `frontend/src/app/router/routes.ts`. `/demo` queda disponible desde el CTA del Dashboard, sin ocupar una entrada permanente en la navegación operativa.

La aplicación mantiene el enrutamiento liviano ya existente, basado en `window.location.pathname`. Nginx aplica fallback a `index.html`, por lo que las rutas directas y el refresh funcionan en el contenedor.

## 3. Dashboard

El Dashboard compone en paralelo endpoints existentes para mostrar:

- total de casos y conformidad estructural;
- total y distribución de desviaciones;
- cantidad de alertas abiertas;
- variante y transición más frecuentes;
- transición con mayor duración observada;
- versión y métricas del modelo activo;
- alertas activas o atendidas recientes.

Los valores provienen de la API. No existen métricas ni scores hardcodeados. No se añadió un endpoint agregador porque los endpoints existentes cubren el resumen sin descargar eventos globales ni duplicar lógica analítica en backend.

## 4. Casos

`/cases` presenta una tabla paginada de 20 filas con código, etapa actual, estado, fuente, recurso asignado e inicio. Permite buscar un `case_code` exacto mediante el endpoint existente y enlaza cada fila con su detalle integral.

## 5. Detalle integral

`/cases/:id` reúne, sin alterar resultados:

- datos principales y etapa actual;
- timeline cronológico de eventos;
- conformidad y secuencias esperada/observada;
- desviaciones y detalle contextual;
- última predicción persistida y sus factores;
- cálculo predictivo explícito iniciado por el usuario;
- alertas del caso y su historial de acciones.

La información se solicita con endpoints específicos por caso; no se descarga el Event Log completo.

## 6. Componentes compartidos

Los componentes compartidos se agrupan bajo `frontend/src/shared`:

- `Layout.tsx`: `PageHeader`, `KpiCard`, `SectionCard` y aviso de dataset;
- `Badges.tsx`: badges de riesgo, severidad, estado de alerta y estado de caso;
- `States.tsx`: estados de carga, error y vacío;
- `format.ts`: fechas, números y porcentajes.

`frontend/src/components/layout` contiene Sidebar, Topbar y AppShell.

## 7. Etiquetas centralizadas

`frontend/src/shared/constants/labels.ts` centraliza las traducciones de estados de caso, estados y acciones de alerta, niveles de riesgo, severidades, tipos de desviación y tipos de evento. Los módulos integrados consumen esas constantes para evitar vocabulario divergente.

## 8. Identidad visual

La interfaz usa una identidad G&V sobria: verde grisáceo oscuro para estructura y acciones principales, superficies claras, bordes discretos y colores semánticos moderados para información, advertencia y peligro. Los tokens están declarados en `frontend/src/styles.css`. No se instaló un framework visual adicional; se reutilizó Tailwind CSS para mantener el bundle y la arquitectura actuales.

## 9. Datos simulados

El Dashboard y el modo demostración muestran un aviso configurable mediante `VITE_DATASET_NOTICE`, cuyo valor por defecto es “Datos simulados de demostración”. La variable está disponible tanto en `.env.example` como en el build de Docker. Este aviso evita presentar el dataset académico como información comercial real.

## 10. Modo demostración

`/demo` consulta predicciones persistidas y selecciona candidatos en tiempo de ejecución:

- HIGH: predicción aplicable, nivel `HIGH` y etiqueta positiva; se prioriza un caso sin alerta existente y luego el mayor score;
- LOW: predicción aplicable, nivel `LOW`; se prioriza el menor score.

El selector permite cambiar a cualquier candidato real devuelto por la API. El flujo no usa ground truth, no fija un `case_code` y no inventa scores. Reproducir una predicción o evaluar una alerta son acciones explícitas mediante botones. Ninguna acción del demo escribe o modifica eventos ni desviaciones.

### Guion de demostración (3–5 minutos)

| Tiempo | Recorrido |
|---|---|
| 00:00–00:30 | Abrir Dashboard y explicar KPIs reales y aviso de datos simulados. |
| 00:30–01:15 | Abrir Minería de Procesos; revisar variante, grafo o transición. |
| 01:15–02:00 | Abrir Desviaciones y navegar desde una fila hacia el caso. |
| 02:00–03:00 | Revisar timeline, conformidad y predicción del caso. |
| 03:00–04:00 | En `/demo`, elegir un candidato HIGH real, reproducir su snapshot y evaluar la alerta explícitamente. |
| 04:00–04:30 | Mostrar el candidato LOW real y explicar “predicción ≠ alerta”. |

Los códigos, snapshots y scores deben leerse del selector durante la exposición; no se documenta un resultado fijo que pueda quedar obsoleto.

## 11. Flujo recomendado de exposición

El recorrido principal es Dashboard → Minería de Procesos → variante/transición → Desviaciones → Caso → Timeline → Predicción HIGH → Alerta → gestión operativa. El recorrido complementario es Caso LOW → predicción persistida → riesgo bajo → ausencia de alerta. Los enlaces cruzados entre casos, desviaciones, predicciones y alertas permiten ambos recorridos.

## 12. Limitaciones

- La aplicación utiliza navegación por documentos y no un router de terceros; esto es compatible con la estructura previa y con el fallback de Nginx, pero no conserva estado local al cambiar de módulo.
- El Dashboard usa visualizaciones CSS simples; no se añadió una librería de gráficos para una única distribución.
- La búsqueda de casos es exacta porque ese es el filtro soportado por el backend actual.
- El frontend conserva algunos componentes visuales específicos de módulos anteriores para no reescribir funcionalidad validada.
- No hay autenticación, agentes ni notificaciones externas; quedan fuera del Sprint 7.
- Las acciones predictivas y de alertas siguen siendo explícitas. El modo demo no automatiza mutaciones operativas.

## Integridad protegida

`backend/scripts/check_data_integrity.py` implementa la metodología `gyv-integrity-v1`: columnas fijas, filas ordenadas por UUID, timestamps UTC con microsegundos, JSON canónico y SHA-256 por líneas UTF-8. El baseline previo a la implementación está en `docs/integrity-sprint7-baseline.json` y debe compararse con una ejecución final usando exactamente el mismo script.
