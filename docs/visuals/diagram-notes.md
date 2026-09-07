# Notas de diagramas

**Proyecto:** `mybank-banking-data-science`. **Producto:** Ciencia de datos bancaria. **Fecha:** 2026-09-07. Proyecto independiente con datos sintéticos; no afirma clientes, patrocinadores o resultados reales.

## Arquitectura de solución

`solution-architecture.svg` separa dos estados con palabras y estilos: ejecución local verificada en índigo y objetivo AWS pendiente en ámbar discontinuo. El color refuerza la diferencia, que también está escrita.

- La banda local se deriva de [arquitectura](../architecture.md), [contrato](../model-card.md) y [evidencia](../../evidence/status.md). Conserva dos laboratorios: clasificación de incumplimiento a 90 días y regresión de duración de incidentes.
- Los generadores producen 8.000 solicitudes y 2.400 incidentes por defecto, antes de excluir etiquetas inmaduras. No representan datos o volumen de un cliente ni carga probada en AWS.
- Train alimenta el pipeline; validación alimenta evaluación/selección, sin intervenir en el ajuste inicial. En clasificación se conserva el pipeline ajustado con train y el umbral elegido en validación. En duración, después de elegir se reajusta con train + validación maduros. Ese refit se resume dentro de evaluación/selección; los detalles están en el contrato técnico.
- El holdout no se evaluó en el flujo verificado. Está reservado por procedimiento y opción CLI, **sin barrera de control de acceso**. El diagrama no representa una bóveda ni un aislamiento de seguridad inexistente.
- Los 20 tests y el entorno nuevo reflejan la evidencia de una ejecución local registrada. No certifican modelos ni demuestran desempeño prospectivo.
- AWS permanece propuesto: S3 → Processing → Training → evaluación → Model Registry → revisión → Batch Transform → S3. La evaluación se representa como un Processing posterior a Training; Pipelines orquesta el flujo. El lote nuevo llega a Batch Transform por una entrada separada.
- La revisión de versión es una decisión humana de diseño. Antes de usar datos reales hacen falta evaluación independiente, gobierno y controles acordados en el [piloto](../pilot.md). El dibujo no automatiza la apertura del holdout.
- No hay recursos cloud, cuentas, regiones, endpoints, costos medidos o clientes representados. Empaquetado, IAM/cifrado, reintentos, reconciliación por ID y pruebas bajo fallas siguen pendientes.

## Lectura Well-Architected

`well-architected.svg` usa los seis pilares confirmados oficialmente: excelencia operacional, seguridad, fiabilidad, eficiencia del rendimiento, optimización de costos y sostenibilidad. [AWS: pilares](https://docs.aws.amazon.com/wellarchitected/latest/framework/the-pillars-of-the-framework.html), [AWS: definiciones](https://docs.aws.amazon.com/wellarchitected/latest/framework/definitions.html).

El mapeo es una interpretación del proyecto. «Decisión de diseño» incluye decisiones adoptadas localmente y propuestas para el entorno objetivo. Sólo «Evidencia local» afirma una comprobación existente. «Por validar en AWS» indica trabajo pendiente. No hay puntajes, sello, certificación o evaluación realizada con AWS Well-Architected Tool.

| Pilar | Evidencia local | Límite |
| --- | --- | --- |
| Excelencia operacional | Tests, registros y entorno reproducible | Falta validar alertas, runbooks y rollback |
| Seguridad | Generadores sin lecturas externas | No acredita IAM, cifrado, red ni protección de datos reales |
| Fiabilidad | Contratos temporales con fixtures | No acredita idempotencia, restauración o disponibilidad cloud |
| Eficiencia del rendimiento | Dos flujos ejecutados | No es un benchmark de carga, memoria ni latencia AWS |
| Optimización de costos | No hay endpoint o despliegue AWS | No se midieron costo por lote ni ahorros |
| Sostenibilidad | Búsqueda y baseline declarados | No se midió energía, utilización ni emisiones |

El diseño por lotes se apoya en [SageMaker Pipelines](https://docs.aws.amazon.com/sagemaker/latest/dg/define-pipeline.html) y [Batch Transform](https://docs.aws.amazon.com/sagemaker/latest/dg/batch-transform.html). Esas referencias describen capacidades, no una implementación existente de este proyecto.

## Edición y comprobaciones

SVG nativos y editables de 1.800 × 1.200, Arial, fondo `#F7F5EF`, títulos `#152837`, índigo `#535CC4` y ámbar `#C88932`. Los textos son nodos `<text>`, sin rasterización ni contornos. Ambos incluyen `title`, `desc`, idioma español y atributos accesibles. No contienen logos, imágenes raster, scripts o dependencias de fuentes remotas.

Se verificaron XML, tamaño del canvas, límites de rectángulos y texto, usando métricas reales de Arial/Arial Bold, y contenido contra evidencia. Las flechas tienen corredores separados. La inspección de una versión renderizada corresponde al agente principal; no se generó PNG en esta entrega.

[sources.json](sources.json) conserva URLs completas, fechas, propósito de fuentes, hashes de documentos locales y de los SVG. Los hashes identifican bytes y no acreditan certificación.
