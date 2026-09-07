# Contrato de demostración y límites de modelos

## Clasificación: incumplimiento a 90 días

- Unidad: solicitud en `decision_date`; target binario `default_90d`; disponible en `decision_date + 90 días`.
- Entradas numéricas: `declared_income`, `debt_to_income`, `historical_arrears`, `customer_tenure_months`. Entradas categóricas: `product_type`, `channel`.
- Datos: generador de 8.000 filas por defecto, semilla 42, una fila diaria terminando en 2025-12-31. Ese calendario artificial extenso permite probar maduración; no representa ciclos económicos reales.
- Cortes: inicios posicionales 65 % y 85 %, seguidos de exclusión por disponibilidad. Los porcentajes no son los tamaños finales después de purgar.
- Modelo: regresión logística, imputación de mediana/moda, escalamiento numérico y one-hot con categoría nueva ignorada.
- Decisión: todos los scores únicos, cero y política de cero alertas; menor costo simulado sujeto a capacidad observada en validación. Desempate por menos alertas y mayor umbral.
- Supuestos por defecto: costo FN 2.000.000 y FP 25.000 unidades monetarias simuladas; presupuesto de alertas 0,12. No son costos observados ni una recomendación para un cliente.
- Reporte: AP, ROC-AUC, matriz de confusión, precision, recall, Brier y log loss frente a prevalencia de train; diagnóstico de calibración por intervalos.

`collection_result`, `balance_30d`, target, IDs y fechas quedan fuera de predictores. El mismo cliente puede reaparecer: el estimando es una solicitud futura de la población operativa. Generalizar a clientes nuevos requiere una evaluación por grupos adicional. La política de umbral fijo no garantiza capacidad futura. No se ajusta un calibrador.

El incremento temporal añadido al logit cambia `P(y|X)` y, como consecuencia, la prevalencia marginal. Se describe como cambio de concepto con prevalencia cambiante; no se asume el caso especial de label shift con `P(X|y)` invariable.

## Regresión: duración de incidentes

- Unidad: incidente al recibir una alerta en `decision_time`; target `resolution_minutes`, en minutos.
- Etiqueta: disponibilidad fija 24 horas después; target sintético menor a ese horizonte. Evita usar la duración del propio target para decidir qué etiquetas ya están disponibles.
- Datos: 2.400 incidentes por defecto, cada seis horas desde 2024-01-01 UTC, semilla 42. Motores y criticidades son categorías de una simulación.
- Entradas: carga CPU, latencia IO, sesiones bloqueadas, retraso de réplica, incidentes previos, tamaño de base, ventana de cambio, hora cíclica, criticidad y familia de motor.
- Candidatos: dummy mediana, lineal, dos Ridge y dos Random Forest declarados en `candidate_specs()` antes de seleccionar.
- Selección: menor MAE de validación, seguido de RMSE y nombre. Se reajusta la especificación elegida en train + validación maduros antes de una eventual evaluación final.
- Reporte: MAE/RMSE en minutos; R², errores por segmento, residuos y proporción de predicciones negativas. R² se informa como nulo si no tiene definición adecuada en un segmento constante o unitario.

Datos posteriores como equipo resolutor, causa final y error posterior al incidente están excluidos. La predicción puntual no es un SLA ni intervalo de predicción.

## Condiciones de uso

Estas demostraciones comprueban ingeniería y método bajo un generador conocido. No establecen rendimiento prospectivo, beneficio económico, justicia por grupos ni ausencia de fuga en datos externos. Antes de un piloto real hay que acordar disponibilidad efectiva, calidad y sesgos de datos, costos, restricciones y revisión humana. No se debe aumentar la complejidad o retocar la selección mirando el período reservado.
