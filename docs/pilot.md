# Piloto: evaluación de modelos y operación por lotes

## Cliente y problema

Dirigido a equipos de datos, riesgo y operaciones que ya disponen de una pregunta concreta y necesitan convertir un análisis exploratorio en una evaluación reproducible. El entregable principal es evidencia para decidir si continuar, corregir o detener un caso de ML.

Se propone elegir **un solo caso**: alertas de riesgo o estimación de duración de incidentes. Comparten ingeniería, pero tienen objetivos, etiquetas, costos y responsables distintos.

## Recorrido propuesto

1. Acordar unidad de análisis, instante de decisión, disponibilidad real de variables/etiquetas y uso autorizado de datos.
2. Construir contrato, cohortes temporales y baseline con un subconjunto autorizado o con los generadores sintéticos del repositorio.
3. Definir candidatos y criterios antes de observar el período reservado. Registrar toda exposición previa relevante; un nuevo nombre de archivo no crea un holdout nuevo.
4. Ejecutar desarrollo y revisar errores, presupuesto de revisión y segmentos con los responsables.
5. Congelar una versión y acordar una evaluación final; si ya se utilizó el período reservado, diseñar una evaluación prospectiva adecuada.
6. Entregar código, arquitectura, trazabilidad, resultados y recomendación de siguiente etapa. Una ejecución en AWS se contrata y verifica como incremento separado.

## Entregables y aceptación

| Entregable | Evidencia de aceptación |
| --- | --- |
| Contrato de datos | Definiciones, unidades, disponibilidad, reglas de nulos e identificadores aprobadas por el dueño del proceso |
| Ejecución reproducible | Versión de código/dependencias, hash de datos autorizados y reporte regenerable |
| Separación temporal | Pruebas de maduración y ausencia de solapamientos bajo el contrato declarado |
| Baseline y evaluación | Comparación completa de candidatos previstos, segmentos e incertidumbre pertinente al caso |
| Política operativa | Costos/criterios provistos por negocio, revisión humana y manejo de capacidad definida |
| Cierre del piloto | Decisión documentada con límites, pendientes y evidencia; resultado negativo también es válido |

No se fija una métrica de éxito universal ni se promete reducción de pérdidas o tiempos sin medición. Las metas de calidad y operación deben pactarse antes de revelar resultados confirmatorios.

## Necesidades para iniciar

Un dueño de proceso, una persona responsable de datos y acceso controlado a definiciones y datos con autorización. El entorno público funciona completamente con datos sintéticos; la información privada de un cliente permanece fuera del repositorio y de sus logs públicos.

## Fuera del alcance inicial

Decisión automática de aprobación crediticia; reemplazo de políticas institucionales; certificación regulatoria; integración con sistemas centrales; disponibilidad continua; nuevas búsquedas para mejorar un resultado ya visto en holdout. Precio, duración y consumo cloud se calculan después de precisar datos, volumen e integraciones.
