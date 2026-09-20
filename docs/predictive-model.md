# Modelo predictivo — Sprint 5

## Problema y target

Sprint 4 detecta desviaciones que ya ocurrieron mediante reglas determinísticas. Sprint 5 estima el riesgo asociado a una desviación futura antes de la próxima transición comercial; no crea alertas.

El target formal es `NEXT_DEVIATION`: para un snapshot en `T`, vale 1 si existe una desviación persistida cuyo `detected_at` pertenece a `(T, siguiente STAGE_CHANGE]`; en caso contrario vale 0. Los labels proceden exclusivamente de PostgreSQL (`events` y `deviations`). El ground truth del generador no se abre ni se importa.

## Snapshots, checkpoints y censura

Se crea un snapshot en cada evento histórico que tenga un `STAGE_CHANGE` posterior. Entre eventos se derivan checkpoints en memoria cada `ML_SNAPSHOT_INTERVAL_HOURS` (12 horas por defecto). No se insertan en `events`.

Un snapshot sin transición futura observable se considera censurado y no entra al entrenamiento. También se excluye un checkpoint si en ese momento el SLA de la etapa o el umbral de inactividad ya fue superado: el objetivo es anticipar, no volver a clasificar un incumplimiento conocido.

## Features

Variables categóricas:

- etapa actual y anterior;
- fuente del caso;
- recurso actual y recurso asignado.

Variables numéricas:

- secuencia y SLA actual, secuencia anterior;
- eventos, cambios de etapa y etapas únicas observadas;
- ocurrencias de la etapa actual;
- horas desde el inicio, en la etapa y desde el evento anterior;
- duración anterior y estadísticas de etapas completadas;
- progreso del proceso;
- conteos de desviaciones anteriores por tipo, estructurales y temporales;
- hora y día de semana.

Se excluyen por diseño `case_id`, `case_code`, `event_id`, etapas/eventos futuros, duración final, `closed_at` futuro, target, escenario, ground truth, variante futura y cualquier timestamp posterior. Los identificadores sólo se conservan fuera de la matriz de features para split y trazabilidad.

## Prevención de leakage

`build_features` vuelve a filtrar eventos y desviaciones por timestamp, aunque el llamador ya entregue una traza. Cada muestra conserva metadata de auditoría y el entrenamiento se detiene si:

- `max(feature_event_timestamp) > snapshot_timestamp`;
- `max(feature_deviation_detected_at) > snapshot_timestamp`;
- aparece una feature prohibida;
- cambia el orden del schema versionado.

Las pruebas verifican además que agregar un evento o una desviación futura no cambia un snapshot pasado.

## Dataset, split y reproducibilidad

El dataset se reconstruye desde PostgreSQL. Su SHA-256 se calcula sobre filas y columnas ordenadas canónicamente. Los casos se dividen aproximadamente 70/15/15 en train, validation y test, estratificando a nivel de caso cuando es posible y usando `random_state=42`. Un caso nunca aparece en dos conjuntos.

El test permanece intocable hasta seleccionar algoritmo y threshold con validation. No se utiliza SMOTE, ADASYN, oversampling ni eliminación artificial de clases.

## Modelos y evaluación

Se comparan:

- `DummyClassifier(strategy="prior")` como baseline no productivo;
- Logistic Regression con `class_weight="balanced"`;
- Random Forest de 200 árboles, `min_samples_leaf=2` y clases balanceadas.

Cada pipeline incluye imputación, `OneHotEncoder(handle_unknown="ignore")`, escalado numérico y estimador. Se calculan accuracy, precision, recall, F1, ROC-AUC, PR-AUC, Brier Score y matriz de confusión.

La selección usa únicamente PR-AUC de validation y F1 como desempate. Si Logistic Regression y Random Forest difieren como máximo 0,02 en PR-AUC, se prefiere Logistic por interpretabilidad. El decision threshold maximiza F1 en validation; no se confunde con los niveles operativos de riesgo.

## Score y niveles de riesgo

`predict_proba` se presenta como “riesgo estimado”, no como probabilidad perfectamente calibrada:

- `LOW`: score menor que 0,40;
- `MEDIUM`: desde 0,40 y menor que 0,70;
- `HIGH`: desde 0,70.

El label binario utiliza el threshold aprendido en validation, que puede ser diferente.

## Artefactos y versionado

El pipeline completo se guarda con joblib bajo `ML_MODEL_DIR`, montado en el volumen Docker `ml_models`. Un sidecar JSON contiene metadata y el SHA-256 calculado después de guardar. Cada ejecución persiste versión, dataset hash, schema, métricas, hiperparámetros, resumen y artifact hash en `ml_model_runs`.

La activación desactiva transaccionalmente la versión anterior sin eliminarla. La API carga el modelo bajo demanda, verifica SHA-256 y mantiene una caché invalidada por id/hash del modelo activo. El backend nunca reentrena durante el arranque.

## Predicción y replay histórico

Sin `as_of`, la referencia es el último evento persistido, no el reloj actual. Con `as_of`, eventos y desviaciones posteriores se ignoran. Si el snapshot ya excedió SLA o inactividad, la respuesta usa `prediction_applicable=false` y no persiste un score engañoso.

El fingerprint combina caso, versión, timestamp y estado observable canónico. Repetir el mismo snapshot reutiliza la predicción existente; un nuevo snapshot crea otra. Logistic Regression expone contribuciones locales `valor transformado × coeficiente`; Random Forest expondría importancia global, nunca causalidad.

## Operación

```bash
docker compose exec backend python -m scripts.build_ml_dataset
docker compose exec backend python -m scripts.train_predictive_model
docker compose exec backend python -m scripts.evaluate_predictive_model
docker compose exec backend python -m scripts.score_cases --limit 100
```

La interfaz está en `/predictions`. Los endpoints son:

- `POST /api/v1/cases/{id}/predict`
- `GET /api/v1/cases/{id}/prediction`
- `GET /api/v1/predictions`
- `GET /api/v1/ml/model`
- `GET /api/v1/ml/evaluation`

## Limitaciones

El score no está calibrado formalmente, el dataset es simulado y el target depende de la cobertura de las reglas del Sprint 4. Las relaciones aprendidas son asociaciones, no causas. La vigilancia con tiempo real y las alertas quedan fuera del Sprint 5.
