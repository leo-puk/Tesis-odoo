# R2 — Evidencia de migración de Odoo

**R2.1** implementa planificación → adquisición → normalización y SQLite → cruce → extracción y recorrido de relaciones → reporte. **R2.2** expone el mismo flujo con una CLI local en inglés y lo verifica con pruebas y una comparación con BM25.

## Uso

Desde `sandbox/r2`, con Python 3.12 y las dependencias de `pyproject.toml`:

```powershell
python -m r2 plan ruta/al/modulo --from 16.0 --to 17.0 --catalog reference/adquisition-final/examples/catalog.json --output-dir plan-nuevo
python -m r2 run ruta/al/modulo --from 16.0 --to 17.0 --catalog reference/adquisition-final/examples/catalog.json --output-dir salida-nueva
```

`plan` inspecciona una carpeta local o un repositorio ya clonado. Lee Python, XML, CSV y manifiestos para detectar dependencias, referencias e importaciones de addons. También examina archivos de texto, documentación y configuración para localizar URLs revisadas. No ejecuta el código ni descarga los enlaces durante la planificación. Cada salto incluye candidatos de fuentes oficiales y guías de mantenimiento. El catálogo conserva las exclusiones de adquisición. Las URLs adicionales deben figurar en `allowed_urls` y las de diffs fijados o PRs que no codifican las versiones pueden declarar `source_bindings` por URL, con `from_version` y `to_version`. `planning.json` registra las URLs propuestas, sus motivos y los avisos de cobertura. Una URL planificada puede fallar o no aportar candidatos al capturarse.

`run` guarda los archivos del planner en `planning/` cuando lo invoca automáticamente. Para ejecutar un plan preparado por separado:

```powershell
python -m r2 run ruta/al/modulo --from 16.0 --to 17.0 --plan plan-nuevo/plan.json --catalog plan-nuevo/catalog.json --bindings plan-nuevo/bindings.json --output-dir salida-manual
```

La ejecución guarda las capturas en `temp_data/` y deja `collection.sqlite`, `crossing.json`, `relations.json`, `report.txt` y `report.json` en la salida indicada. El módulo se inspecciona de forma estática. Los datos de entrada se conservan.

El flujo también se puede invocar desde Python con `r2.workflow.run_workflow`. Devuelve el reporte y la evidencia intermedia. La CLI se encarga de guardar las vistas JSON y de texto.

Para repetir la consulta sin descargar ni reconstruir la colección:

```powershell
python -m r2 query ruta/al/modulo --db salida-nueva/collection.sqlite --from 16.0 --to 17.0 --layer python --depth 3 --limit 10 --format json
python -m r2 query ruta/al/modulo --db salida-nueva/collection.sqlite --from 16.0 --to 17.0 --layer python --depth 3 --limit 10 --engine bm25 --format json
python -m r2 validate-output salida-nueva/report.json
python -m unittest discover -s tests -v
```

`search-units` es un alias de `query`. Para preparar la colección por separado, usa `capture-plan` y luego `build` indicando el `inventory.json` generado. `cross`, `extract-relations` y `export` permiten inspeccionar las salidas de cada etapa. Las bases anteriores se reconstruyen con `build` a partir del inventario y los bindings.

## Reporte y alcance de la evidencia

- `bindings.json` tiene una clave `sources` que mapea IDs del plan a `from_version` y `to_version`, en formato `major.minor`. También puede registrar revisiones y `migration_id` explícitas. Los materiales cuya versión es desconocida pueden servir de contexto en un camino, si las versiones conocidas son compatibles. El reporte exige ambos extremos de versión para mostrar un cambio.
- La primera vista presenta hasta diez bloques de diff distintos en el salto y capa consultados. Deduplica copias exactas del mismo hunk y calcula los totales antes del límite. Un bloque se presenta como candidato y conserva su URL, localizador y líneas añadidas o eliminadas.
- El filtro usa la capa del archivo y añade XML cuando una línea modificada contiene un selector XPath con un atributo extraído explícitamente. El reporte distingue las capas de la evidencia de la capa del archivo. Un candidato puede aparecer en el conteo de más de una capa.
- El recorrido parte de coincidencias técnicas tipadas del cruce y explora hasta tres saltos. El reporte ordena por distancia, estado de normalización e ID estable. La profundidad cero identifica el cruce directo. El archivo `relations.json` conserva el vecindario de diagnóstico y el reporte usa únicamente caminos compatibles con el intervalo.
- Cada resultado del grafo conserva el camino, las identidades compartidas y la ubicación en el módulo. BM25 usa las mismas unidades de diff elegibles, versión, capa y límite. Las coincidencias del índice léxico llevan un puntaje.

## Evaluación

`python -m r2 evaluate evaluacion.json --db salida-nueva/collection.sqlite --repeats 3` compara resultados sobre la misma colección y los mismos parámetros. El JSON de entrada contiene:

| Campo | Contenido |
|---|---|
| `reviewer`, `collection_revision` | Revisor responsable y revisión exacta de la colección. |
| `references` | Objeto por ID de cambio de referencia con `migration_id`, `from_version`, `to_version` y `available_unit_ids` adjudicados para C1. Una lista vacía representa un cambio evaluable sin evidencia aplicable. |
| `queries` | Lista con `id`, `module` relativo al JSON, `input_revision`, versiones, `layer`, `maximum_hops`, `limit`, `reference_ids` y, cuando corresponda, `module_name`. |
| `queries[].judgments` | Objeto por `change_id` de la salida, con `relevant` booleano y `reference_ids` específicos de la consulta. Una entrada pertinente sin referencias se registra como hallazgo fuera de la muestra. |

La salida calcula C1 global y conteos por migración y salto, P1 y C2 por consulta, conformidad estructural de V1 y muestras T1. Ante juicios faltantes se devuelve `null` para los indicadores afectados. T1 termina con la primera vista y el resumen renderizados y serializados. Se reportan las repeticiones y el estado de caché. Los juicios y evidencias de los 30 MIG excluidos de la construcción, la revisión de V1 en inglés y el protocolo independiente completan la evaluación de tesis.

`python -m examples.run_evaluation_demo --output salida-demo-nueva` muestra el formato con un módulo OCA local y juicios sintéticos de demostración.

[Requisitos](REQUISITOS.md) · [Contexto y cambios](CONTEXTO_PROYECTO.md)
