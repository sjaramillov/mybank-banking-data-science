# Base técnica: classification

Documentación técnica del laboratorio. La procedencia y los cambios editoriales están registrados en [provenance](../provenance.md).

## Contrato temporal

- La unidad es una solicitud de crédito en `decision_date`.
- El label es incumplimiento dentro de los 90 días posteriores.
- `label_available_at = decision_date + 90 días` representa cuándo el outcome es definitivo.
- `validation_start` es el as-of de entrenamiento: train solo usa labels disponibles en esa fecha.
- `test_start` es el as-of de congelación: validation solo usa labels disponibles en esa fecha.
- Las solicitudes cuyos labels aún no han madurado se purgan; por eso train, validation y holdout no suman el total del dataset.
- Las fechas sintéticas tienen separación diaria para que incluso 1.000 filas permitan dos ventanas de maduración de 90 días.

## Contrato de features y pipeline

- Solo se usan variables conocidas en `decision_date`.
- `collection_result` y `balance_30d` son trampas deliberadas de leakage.
- `label_available_at`, `customer_id`, timestamps y target son metadatos, no predictores.
- Imputación, escalamiento y one-hot encoding se ajustan dentro del `Pipeline` usando train.
- `OneHotEncoder(handle_unknown="ignore")` permite categorías futuras sin aprenderlas anticipadamente.
- El mismo cliente puede reaparecer porque el estimando principal es una solicitud futura de la población operativa. Para generalizar a clientes nunca vistos se requiere además una evaluación por grupos.

## Threshold y capacidad

- El threshold se selecciona exclusivamente con validation.
- Se evalúan todos los scores únicos, cero y una política explícita de cero alertas; no una grilla aproximada.
- `max_alert_rate` es un **presupuesto de diseño observado en validation**, no una garantía fuera de muestra.
- En holdout se reportan `alert_rate`, capacidad de referencia y `design_budget_breached`.
- Si la capacidad fuera una restricción dura en producción, la política tendría que incluir un top-k determinista por lote además del threshold.

## Calibración

La solución no ajusta un calibrador: solo diagnostica calibración mediante:

- Brier score;
- log loss;
- tabla por intervalos con probabilidad media y tasa observada;
- comparación contra un predictor constante con la prevalencia de train.

Un Brier bajo no basta en eventos raros. Para calibrar de verdad se necesitaría un conjunto separado o validación anidada, sin tocar el holdout.

## Límites

El laboratorio demuestra una metodología mínima, no un modelo listo para producción. Faltan definición con dueños de negocio, datos reales con lineage, validación independiente, intervalos de incertidumbre, fairness por segmentos, pruebas de estrés, seguridad, SLO, monitoreo continuo y gobierno de cambios. El costo constante por FN/FP también es una simplificación: en crédito real puede depender de exposición y recuperación.
