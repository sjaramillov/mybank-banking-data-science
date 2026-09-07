# Base técnica: incident_duration

Documentación técnica del laboratorio. La procedencia y los cambios editoriales están registrados en [provenance](../provenance.md).

## Contrato del problema

- **Unidad:** un incidente de base de datos en el instante de alerta.
- **Target:** `resolution_minutes`, duración final en minutos.
- **Instante de decisión:** `decision_time`.
- **Disponibilidad del label:** `label_available_at`, 24 horas después.
- **Predicción:** estimación puntual; no debe interpretarse como garantía o SLA.
- **Uso posible:** priorización y planeación de capacidad, siempre con criterios
  operativos adicionales y sin automatizar decisiones críticas solo por el score.

El target sintético se limita a menos de 24 horas. La demora fija de disponibilidad
es conservadora y no depende del valor del target. Esto evita un error sutil: excluir
casos largos porque todavía no terminaron crea censura informativa y hace que el
pasado parezca artificialmente más fácil.

## Split temporal y *as-of*

El generador produce eventos cada seis horas. El flujo:

1. Ordena por `decision_time`.
2. Usa el 65 % posicional como inicio de validation.
3. Usa el 85 % como inicio del holdout.
4. En train conserva solo labels disponibles al comenzar validation.
5. En validation conserva solo labels disponibles al comenzar el holdout.
6. Purga las filas inmaduras entre períodos.
7. No calcula resultados del holdout salvo con `--open-holdout`.

La fecha no entra como feature cruda. La hora se codifica de forma cíclica con seno
y coseno usando información ya conocida al momento de la alerta.

## Features y fuga

Las features permitidas describen carga, latencia, bloqueos, réplica, historial,
tamaño, ventana de cambio, hora, criticidad y familia de motor. Los faltantes se
imputan dentro del pipeline.

Las siguientes columnas se crean para demostrar la exclusión de información futura:

- `resolved_at`;
- `resolution_team`;
- `final_root_cause`;
- `post_incident_error_rate`;
- `incident_id` y metadatos temporales;
- el propio target.

Aunque alguna sea muy predictiva, nace después de la decisión o funciona como
identificador. Usarla sería fuga, no inteligencia del modelo.

## Comparación de modelos

Todos reciben exactamente las mismas filas, features y métrica de selección:

| Familia | Razón para incluirla |
|---|---|
| Dummy mediana | Responde si el ML agrega valor frente a una constante robusta. |
| Lineal | Baseline interpretable; revela cuánto explica una relación aditiva. |
| Ridge | Controla coeficientes correlacionados mediante regularización L2. |
| Random Forest | Captura interacciones y umbrales sin imponer linealidad. |

Los candidatos se entrenan solo con train. Gana el menor MAE de validation; los
empates se resuelven por RMSE y luego por nombre, de forma determinista. Una vez
elegida la especificación, se reajusta sobre train + validation, ya que todos esos
labels están disponibles al comienzo del holdout. No se cambian parámetros después.

## Cómo leer las métricas

- **MAE:** magnitud promedio del error en minutos. Es interpretable y menos sensible
  a casos extremos que RMSE.
- **RMSE:** penaliza más los errores grandes. Si se aleja mucho del MAE, revise la
  cola de incidentes difíciles.
- **R²:** mejora relativa frente a predecir la media en esa muestra; puede ser
  negativo. No mide error en minutos ni garantiza utilidad operacional.
- **Mediana y p90 del error absoluto:** caso típico y cola operacional.
- **Residuo medio:** aquí se define como `observado - predicho`; positivo significa
  que el modelo subestima duración.
- **Error por segmento:** descubre si una métrica global oculta degradación en un
  tier o motor. Segmentos pequeños requieren intervalos e investigación adicional.

La correlación entre error absoluto y predicción es apenas una alarma sencilla de
heterocedasticidad. No reemplaza gráficos de residuos, intervalos de predicción,
bootstrap ni monitoreo con volumen suficiente.

## Límites deliberados

- Los datos son sintéticos y el patrón no representa una operación bancaria real.
- No hay inferencia causal.
- No hay intervalos de confianza ni de predicción.
- No se optimiza una función económica específica; MAE es el criterio declarado del laboratorio.
- El diagnóstico de residuos es básico y no prueba normalidad ni homocedasticidad.
- No hay búsqueda extensa: el objetivo es demostrar metodología, no agotar tuning.
- Un despliegue real requeriría definición de SLA, seguridad, gobierno, lineage,
  monitoreo, champion/challenger y aprobación de riesgo de modelo.

## Referencias técnicas

- [scikit-learn: common pitfalls and recommended practices](https://scikit-learn.org/stable/common_pitfalls.html)
- [scikit-learn: Pipeline](https://scikit-learn.org/stable/modules/compose.html#pipeline)
- [scikit-learn: model evaluation for regression](https://scikit-learn.org/stable/modules/model_evaluation.html#regression-metrics)
- [scikit-learn: time-related feature engineering](https://scikit-learn.org/stable/auto_examples/applications/plot_cyclical_feature_engineering.html)
