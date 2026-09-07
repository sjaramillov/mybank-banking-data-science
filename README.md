# Ciencia de datos bancaria

![Ciencia de datos bancaria: imagen conceptual del proyecto](docs/visuals/cover.png)

**Evaluación reproducible de modelos antes de integrarlos en una operación.**

`mybank-banking-data-science` es un proyecto de ciencia de datos para equipos de entidades financieras. Permite estudiar clasificación de riesgo y duración de incidentes mediante modelos reproducibles, datos sintéticos y validación temporal.

Para equipos que necesitan comprobar qué información usó un modelo, cuándo estaba disponible, cómo se eligió una política y qué evidencia respalda sus resultados. El repositorio reúne dos demostraciones locales con datos completamente sintéticos, documentación técnica de origen y una propuesta de piloto.

| Demostración | Decisión que permite estudiar | Estado |
| --- | --- | --- |
| Clasificación de riesgo a 90 días | Ordenar solicitudes y estudiar una política de alertas según costos simulados y capacidad de revisión | Implementada localmente; validación de desarrollo; holdout cerrado |
| Duración de incidentes | Comparar estimadores de minutos de resolución y revisar errores por segmento operativo | Implementada localmente; validación de desarrollo; holdout cerrado |

La segunda demostración es regresión de duración operacional; no estima riesgo crediticio. Ningún resultado de estas simulaciones acredita desempeño en una entidad financiera ni implica una decisión automática de crédito.

## Ejecutar la demo

Requisitos: Python 3.13 y [uv](https://docs.astral.sh/uv/). Desde la raíz del repositorio:

```bash
uv sync --locked
uv run python scripts/verify.py
```

El comando ejecuta tests y ambos flujos de desarrollo. Guarda registros y reportes JSON en `artifacts/verification/`. No abre ni evalúa los holdouts. Los reportes de la extracción comprobada están en [evidence](evidence/status.md).

Para recorrer solamente el caso principal:

```bash
uv run python scripts/verify.py --lab classification --mode demo
```

Alternativa con un entorno Python 3.13 propio:

```bash
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/verify.py
```

`requirements.txt` fija versiones; `uv.lock` añade hashes de distribución y resolución. No se descarga ni requiere un dataset externo. Los generadores producen los datos en memoria durante cada ejecución.

## Qué puede comprobar un cliente

1. El modelo aprende de etiquetas disponibles en la fecha simulada, con filas inmaduras excluidas.
2. Imputación, escalamiento y categorías se aprenden dentro del entrenamiento.
3. Ranking, calidad de probabilidades y política de decisión se reportan por separado.
4. Los modelos de duración compiten contra un baseline de mediana con criterios declarados.
5. Cada ejecución deja evidencia y conserva separado el período reservado.

La demostración inicial puede acompañarse de un piloto con un proceso, un responsable y criterios de aceptación acordados. [Alcance del piloto](docs/pilot.md).

## Documentación

- [Base de clasificación](docs/base/classification.md) y [base de duración](docs/base/incident_duration.md): conocimiento técnico conservado de los laboratorios anteriores.
- [Arquitectura](docs/architecture.md): implementación local actual y objetivo AWS por lotes, pendiente de implementar.
- [Contrato de datos y modelos](docs/model-card.md): supuestos, variables y límites.
- [Guion de demostración](docs/demo.md): recorrido y lectura de resultados.
- [Procedencia](docs/provenance.md) y [manifiesto SHA-256](docs/source-manifest.json): extracción selectiva, cambios y exclusiones.
- [Evidencia ejecutada](evidence/status.md): comprobaciones y alcance real.

## Alcance actual

No hay endpoint, base de clientes, integración bancaria, despliegue AWS ni costos de nube medidos. No se publican datos reales, credenciales, logos, material de evaluación ni notebooks con respuestas de terceros. El código es una base verificable para pilotos; falta validar calidad, equidad, utilidad y operación con datos autorizados antes de utilizarlo en decisiones reales.

## Conversar sobre un piloto

El [plan de piloto](docs/pilot.md) propone alcance y criterios de aceptación.
Puedes contactar a Sebastián Jaramillo desde su [perfil de GitHub](https://github.com/sjaramillov)
para adaptar la demostración a un proceso concreto. [Autoría y condiciones de uso](NOTICE.md).

## Arquitectura visual

La [galería del proyecto](docs/visuals/README.md) reúne la portada, la arquitectura de solución y la revisión de AWS Well-Architected. Los diagramas identifican los componentes existentes y el diseño propuesto, con fuentes oficiales y evidencia del proyecto. Incluyen PNG para compartir y SVG editables.
