# Demostración guiada

## Pregunta inicial

«¿Podemos reconstruir lo que sabía el modelo en la fecha de decisión y explicar qué hace con un presupuesto limitado de revisión?»

Abra `docs/base/classification.md` para ver el conocimiento ya construido y `docs/architecture.md` para distinguir la ejecución actual del diseño de nube.

## Recorrido local

1. Ejecute `uv run python scripts/verify.py --lab classification` desde la raíz.
2. Abra `artifacts/verification/classification-development.json`.
3. Revise `sizes` y `as_of`: las filas históricas con etiquetas inmaduras están excluidas; no se hace una separación aleatoria.
4. Compare `average_precision` con la prevalencia de validación. Revise Brier/log loss y sus referencias; un score útil para ordenar no implica probabilidades calibradas.
5. Lea la matriz de confusión, alertas y costo simulado. El threshold fue elegido usando esa misma validación; estos valores describen desarrollo, no una prueba independiente de esa elección.
6. Compruebe `holdout_opened: false` y ausencia de clave `holdout`.

El caso de duración usa `uv run python scripts/verify.py --lab incident_duration`. Su JSON contiene `holdout_status: CLOSED`, comparación completa de candidatos, error por segmento y diagnósticos de residuos. Las métricas de validación provienen de los modelos entrenados sólo en train; el artefacto final se reajusta después con los datos de desarrollo maduros.

## Conversación de piloto

Explique qué cambia al sustituir el generador por datos autorizados: procedencia, disponibilidad, validez de las etiquetas, representatividad, costos y revisión humana. Proponga una pregunta y criterio de aceptación específicos. Use `docs/pilot.md` como alcance inicial.

No ejecute opciones de apertura del holdout durante una demostración comercial de desarrollo. El repositorio conserva esa capacidad explícita del laboratorio para una evaluación final previamente congelada; el runner público de verificación no ofrece esa opción.
