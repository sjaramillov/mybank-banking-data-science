# Avisos de terceros

`mybank-banking-data-science` · Revisión: 7 de septiembre de 2026.

La [licencia Apache 2.0 del proyecto](LICENSE) cubre el material original según
su [alcance](docs/licensing.md). Las bibliotecas, herramientas, marcas y
referencias siguientes mantienen sus propios términos. Este archivo identifica
dependencias y fuentes; no las relicencia ni sustituye sus avisos completos.

## Dependencias de Python

Las bibliotecas se descargan mediante el gestor de paquetes. Este repositorio
no incorpora su código fuente, wheels ni entornos virtuales. Las versiones
proceden de [uv.lock](uv.lock) y [requirements.txt](requirements.txt); las
licencias se contrastaron con los metadatos oficiales de cada versión en PyPI.

| Componente | Versiones fijadas | Licencia declarada y fuente |
| --- | --- | --- |
| NumPy — directa | 2.5.2; 2.4.6 para Python anterior a 3.12 | `BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0`: [2.5.2](https://pypi.org/project/numpy/2.5.2/), [2.4.6](https://pypi.org/project/numpy/2.4.6/) |
| pandas — directa | 3.0.5 | [BSD-3-Clause](https://pypi.org/project/pandas/3.0.5/) |
| scikit-learn — directa | 1.9.0 | [BSD-3-Clause](https://pypi.org/project/scikit-learn/1.9.0/) |
| SciPy | 1.18.1; 1.17.1 para Python anterior a 3.12 | BSD-3-Clause: [1.18.1](https://pypi.org/project/scipy/1.18.1/), [1.17.1](https://pypi.org/project/scipy/1.17.1/) |
| cloudpickle | 3.1.2 | [BSD-3-Clause](https://pypi.org/project/cloudpickle/3.1.2/) |
| joblib | 1.6.0 | [BSD-3-Clause](https://pypi.org/project/joblib/1.6.0/) |
| narwhals | 2.25.0 | [MIT](https://pypi.org/project/narwhals/2.25.0/) |
| python-dateutil | 2.9.0.post0 | [BSD-3-Clause; Apache-2.0 también cubre las contribuciones indicadas por su aviso](https://github.com/dateutil/dateutil/blob/2.9.0.post0/LICENSE) |
| six | 1.17.0 | [MIT](https://pypi.org/project/six/1.17.0/) |
| threadpoolctl | 3.6.0 | [BSD-3-Clause](https://pypi.org/project/threadpoolctl/3.6.0/) |
| tzdata — dependencia condicional del lock | 2026.3 | [Apache-2.0, con los avisos de los datos incluidos en el paquete](https://pypi.org/project/tzdata/2026.3/) |

El entorno de desarrollo verificado utiliza Python 3.13. El lock también
contiene variantes para otras versiones y plataformas; esta tabla las incluye
sin afirmar que se ejecutaran todas.

Las licencias principales de pandas y SciPy no agotan los avisos de sus
componentes incluidos. Las distribuciones de NumPy también pueden incorporar
bibliotecas numéricas con términos adicionales, según plataforma y formato.
Consulta los archivos de licencia de los paquetes exactos que distribuyas.
Si preparas un ejecutable, contenedor o bundle, conserva los avisos de copyright,
licencias y exenciones exigidos por todos los componentes efectivamente incluidos.
Instalar una dependencia no la convierte en material original de este proyecto.

## Herramientas y servicios de desarrollo

Los workflows referencian Actions por SHA y descargan herramientas durante CI;
sus implementaciones no se distribuyen dentro de este repositorio. Cada
herramienta conserva los términos de su versión:

- [actions/checkout 7.0.1](https://github.com/actions/checkout/blob/v7.0.1/LICENSE).
- [actions/setup-python 7.0.0](https://github.com/actions/setup-python/tree/v7.0.0).
- [uv 0.11.17](https://github.com/astral-sh/uv/tree/0.11.17).
- [Gitleaks 8.30.1](https://github.com/gitleaks/gitleaks/tree/v8.30.1).

GitHub Actions y CodeQL se utilizan bajo los términos correspondientes del
proveedor. La licencia del proyecto no incluye esos servicios ni promete su
disponibilidad. [CairoSVG](https://cairosvg.org/) se utilizó para renderizar los
diagramas y no está incorporado al código distribuido; su licencia permanece
separada de la del material original renderizado.

## Datos, portadas y diagramas

Los dos laboratorios contienen generadores sintéticos escritos en el proyecto.
No se redistribuyen datasets bancarios externos ni datos de clientes. Los
reportes publicados corresponden a verificaciones sintéticas y no demuestran
resultados con una entidad financiera. La reserva del holdout es metodológica;
la licencia no convierte el generador ni su semilla públicos en información secreta.

La portada se generó con IA como ilustración conceptual. Los diagramas son
composiciones editables de texto y formas SVG del proyecto, acompañadas de sus
PNG renderizados. Se comparten conforme al [alcance de licencia](docs/licensing.md),
en la medida de los derechos que el titular pueda otorgar, sin prometer
exclusividad sobre elementos generados. [assets.json](docs/visuals/assets.json)
registra su creación y hashes; esos hashes no prueban titularidad de derechos.

Los SVG mencionan Arial como familia tipográfica, pero no incorporan ni
redistribuyen archivos de fuentes. No contienen scripts, logos, imágenes
externas ni recursos remotos. Los nombres de tecnologías y servicios se usan
para identificar componentes y propuestas técnicas.

## Marcos y referencias de AWS

Las arquitecturas y la revisión de seis pilares se apoyan en documentación
oficial de AWS: [Well-Architected](https://docs.aws.amazon.com/wellarchitected/latest/framework/the-pillars-of-the-framework.html),
[SageMaker Pipelines](https://docs.aws.amazon.com/sagemaker/latest/dg/define-pipeline.html)
y [Batch Transform](https://docs.aws.amazon.com/sagemaker/latest/dg/batch-transform.html).
El registro de [fuentes técnicas](docs/visuals/sources.json) identifica qué
afirmación respalda cada enlace.

El mapeo de decisiones, evidencia y trabajo pendiente es una interpretación
propia. No constituye certificación, revisión oficial, afiliación ni aval de
AWS; tampoco acredita un despliegue. Los enlaces no redistribuyen ni relicencian
la documentación del proveedor. AWS y los nombres de sus servicios son marcas
de Amazon.com, Inc. o sus afiliadas; sus derechos permanecen separados de esta licencia.
