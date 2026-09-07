# Procedencia y publicación

## Alcance exclusivo

Este proyecto reúne dos laboratorios propios: clasificación de riesgo y estimación de duración de incidentes. Su alcance es la evaluación reproducible de modelos para entidades financieras con datos sintéticos. Las fuentes técnicas se identifican mediante alias estables y hashes; no se atribuye la demostración a un cliente concreto.

## Base conservada

La extracción parte de dos laboratorios locales propios preexistentes: clasificación de incumplimiento sintético y regresión de duración de incidentes sintéticos. Sus referencias técnicas pasan a `docs/base/`; esta capa conserva el método. README, arquitectura, contrato público, guion de demo, piloto y evidencia constituyen la documentación adicional orientada a clientes.

El [manifiesto](source-manifest.json) asigna alias estables a las fuentes privadas, identifica cada archivo fuente/destino con SHA-256 y declara cambios. No incluye rutas personales del equipo. Se conservan nombres de módulos y funciones para minimizar cambios de comportamiento. La estructura de distribución y dependencias se normaliza en una raíz común.

## Confirmación de los datos

Ambos `datos.py` generan observaciones mediante `numpy.random.default_rng(seed)` y reglas escritas en el módulo. Se revisó que no leen archivos, APIs ni conexiones externas. Durante la verificación se generaron fixtures y datos sintéticos nuevos **en la copia**, sin regenerar ni modificar originales. No se copiaron CSV, datos de clientes ni predicciones históricas.

Las categorías de motores de base de datos son etiquetas descriptivas en una simulación. No señalan un cliente, patrocinio o certificación. Los costos de error de clasificación son supuestos ilustrativos; no provienen de una entidad financiera.

## Exclusiones deliberadas

- Documentos privados ajenos a la solución y materiales recibidos de terceros.
- Entornos virtuales, caches, historiales Git, notebooks con outputs previos, modelos serializados y archivos de datos.
- Logos, capturas, identidad visual, credenciales, estados de infraestructura e identificadores de cuentas.

El proyecto distribuye el código y la documentación técnica propios seleccionados. Las dependencias conservan sus licencias y avisos. La trazabilidad de archivos no sustituye la revisión de derechos o dependencias para una publicación posterior.

## Límites de trazabilidad

Un hash acredita identidad de bytes, no autoría, licencia ni ausencia histórica de exposición. Las métricas de desarrollo anteriores pueden haberse visto. En esta ejecución no se abrió el holdout ni se ajustó la búsqueda, los modelos, costos o umbrales para mejorar sus cifras. El generador y la semilla son públicos, por lo que la reserva es metodológica, no confidencial.

Si se modifica un archivo derivado, debe registrarse la razón y actualizarse su hash de destino. Las revisiones futuras deben conservar el hash original para poder reconstruir el origen.
