# Estado comprobado — 2026-09-07

**Demo local verificada con datos sintéticos. AWS es una propuesta. Ambos holdouts permanecieron sin evaluar en esta ejecución.**

## Ejecución

Primero se verificó la extracción con un entorno preexistente. Después se creó un **entorno virtual nuevo** en el repositorio final mediante `uv sync --locked` y se ejecutó `uv run python scripts/verify.py --output evidence/2026-09-07-clean`. Ambos comandos terminaron con exit 0. El intérprete fue Python 3.13.12 en macOS ARM64. Las diez dependencias instaladas y el hash del lock figuran en [environment.json](2026-09-07-clean/environment.json); las ejecuciones están en [run.json](2026-09-07-clean/run.json). Los dos JSON de desarrollo coinciden exactamente con los de la primera comprobación.

| Comprobación | Resultado | Evidencia |
| --- | --- | --- |
| Tests de clasificación | 9 tests, exit 0 | [registro](2026-09-07-clean/classification-tests.log) |
| Desarrollo de clasificación | exit 0; `holdout_opened: false` | [JSON](2026-09-07-clean/classification-development.json) |
| Tests de duración | 11 tests, exit 0 | [registro](2026-09-07-clean/incident_duration-tests.log) |
| Desarrollo de duración | exit 0; `holdout_status: CLOSED` | [JSON](2026-09-07-clean/incident_duration-development.json) |
| Instalación limpia | Nuevo `.venv`, `uv sync --locked`, exit 0 | [entorno y lock](2026-09-07-clean/environment.json) |
| Resolución de dependencias | `uv lock --check --offline`, exit 0 | Lock de la base conservado y renombrado |
| Integridad de extracción | Hashes de destino del manifiesto comparados contra archivos, sin diferencias | [manifiesto](../docs/source-manifest.json) |

Los tests verifican maduración, cohortes, columnas excluidas, métricas con cálculos conocidos, restricciones de alertas, categorías nuevas/nulos y selección. Los 20 tests son comprobaciones de contratos bajo fixtures sintéticos; no certifican calidad bancaria, seguridad de producción o ausencia universal de fugas.

## Resultados de desarrollo y lectura limitada

| Caso | Train | Validación | Holdout reservado | Filas inmaduras excluidas |
| --- | ---: | ---: | ---: | ---: |
| Clasificación | 5.111 | 1.511 | 1.200 | 178 |
| Duración | 1.557 | 477 | 360 | 6 |

Las sumas son 8.000 y 2.400 filas respectivamente, incluyendo las excluidas. Los tamaños se calculan desde cada ejecución del generador; los porcentajes posicionales de corte no equivalen a estos tamaños después de maduración.

En clasificación, la validación registra 19 verdaderos positivos, 130 falsos positivos, 24 falsos negativos y 1.338 verdaderos negativos. Precision = 19 / 149 = **12,75 %**, recall = 19 / 43 = **44,19 %**. Con los costos simulados declarados, el costo es `24 × 2.000.000 + 130 × 25.000 = 51.250.000` unidades monetarias simuladas. Esa cifra no es una pérdida observada ni ahorro de un cliente. El umbral se seleccionó con esa misma validación, por lo que su resultado no es una evaluación independiente de selección.

En duración, el modelo seleccionado obtuvo **MAE 16,14 minutos** y **RMSE 20,49 minutos** en validación. Los candidatos y sus resultados completos están en el JSON; son resultados sobre un generador conocido, no una promesa de tiempos operativos. Se conservaron modelos, hiperparámetros y regla de elección de la base, sin buscar una mejora durante la extracción.

## Lo que no se ha comprobado

- Instalación en un host sin caché previa de paquetes. Se comprobó un entorno virtual nuevo desde el lock, sin modificar la resolución; no se auditó qué distribuciones procedieron de caché o descarga.
- Ejecución en Linux/Windows, contenedor, CI remoto o AWS; permisos cloud, costos y operación bajo fallas.
- Calidad con datos de un cliente, incertidumbre de generalización, equidad por segmentos, calibración ajustada o rentabilidad.
- Ausencia de exposición histórica a holdout en trabajos anteriores. Aquí no se calculó ni consultó su desempeño. Sólo se inspeccionaron metadatos de corte/tamaño y los contratos del generador.
- Aislamiento de acceso al holdout: el generador es público y la CLI original conserva una opción explícita. El runner de verificación no la activa. Es una reserva metodológica, no un control de acceso.

La lectura crítica final confirmó el alcance de los dos laboratorios, que sus generadores no leen datos externos y que los archivos seleccionados no contienen datos personales, identificadores operativos ni secretos detectados en la revisión. Los nombres comerciales de motores son categorías descriptivas de una simulación, sin relación comercial afirmada. Los hashes de destino siguen coincidiendo con el manifiesto.

Los originales permanecieron sin cambios y no se copiaron sus historiales Git. La publicación remota, licencia y controles comunes del proyecto se gestionan por separado.
