# R2 — Evidencia de migración de Odoo

**R2.1** implementa planificación → adquisición → normalización y SQLite → cruce → extracción y recorrido de relaciones → reporte. **R2.2** expone el mismo flujo con una CLI local en inglés y lo verifica con pruebas y una comparación con BM25.

## Paso a paso en Windows

Los comandos de esta guía se ejecutan en PowerShell. El ejemplo usa el módulo incluido `sale_advance_payment` y la migración 16.0 a 17.0. Usa Python 3.12, según el rango declarado en `pyproject.toml`. Para trabajar con tu módulo, cambia la variable `$modulo`, su nombre técnico y las versiones.

### 1. Integrar la entrega en dev

Si recibiste el bundle del planner, abre PowerShell y ejecuta lo siguiente desde tu clon. Si ya integraste esta entrega, continúa con el paso 2.

```powershell
Set-Location -LiteralPath "C:\Users\USUARIO\Desktop\Clases\TESIS\repo odo\Tesis-odoo"
git switch dev
git status --short
git fetch "C:/Users/USUARIO/Documents/Codex/2026-11-19/new-chat/outputs/Tesis-odoo-R2-guia.bundle" dev
if ($LASTEXITCODE -ne 0) { throw "Falló la lectura de la entrega" }
git merge --ff-only FETCH_HEAD
if ($LASTEXITCODE -ne 0) { throw "Revisa el estado de tu rama antes de continuar" }
```

Si tienes cambios locales, consérvalos antes de integrar la entrega. El bundle de esta guía incluye el planner y la documentación de funciones.

### 2. Preparar Python y las dependencias

Desde la raíz del clon:

```powershell
Set-Location -LiteralPath "sandbox/r2"
py -3.12 --version
py -3.12 -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Instala Python 3.12 y vuelve a ejecutar este paso" }
& .\.venv\Scripts\python.exe -m pip install -e .
if ($LASTEXITCODE -ne 0) { throw "Revisa el error de instalación antes de continuar" }
& .\.venv\Scripts\python.exe -m r2 --help
```

La instalación requiere acceso al índice de paquetes. Los comandos siguientes usan directamente el Python del entorno virtual.

### 3. Elegir el módulo y las versiones

```powershell
$modulo = (Resolve-Path -LiteralPath "examples/original_module").Path
$nombreModulo = "sale_advance_payment"
$origen = "16.0"
$destino = "17.0"
$marca = Get-Date -Format "yyyyMMdd-HHmmss-fff"
$plan = "temp_data/plan-$marca"
$salida = "temp_data/ejecucion-$marca"
$catalogo = "reference/adquisition-final/examples/catalog.json"
```

Para analizar tu propio módulo, asigna a `$modulo` la ruta de su carpeta y a `$nombreModulo` el nombre técnico de su addon. El planner también acepta un repositorio local con varios addons. Para revisar resultados por módulo, ejecuta cada consulta sobre la carpeta de ese módulo. El nombre técnico explícito se usa en el cruce para resolver sus identificadores.

El catálogo de ejemplo aporta las exclusiones configuradas en el proyecto. Para una evaluación académica, usa el catálogo correspondiente a tus casos reservados.

### 4. Generar e inspeccionar las URLs

```powershell
& .\.venv\Scripts\python.exe -m r2 plan "$modulo" --from $origen --to $destino --catalog "$catalogo" --output-dir "$plan"
if ($LASTEXITCODE -ne 0) { throw "Revisa el error del planner" }
Get-Content -LiteralPath "$plan/planning.json" -Encoding utf8
Get-Content -LiteralPath "$plan/plan.json" -Encoding utf8
```

El planner escribe cuatro archivos. `plan.json` contiene las URLs que descargará adquisición. `catalog.json` conserva las reglas de admisión y añade los candidatos oficiales generados. `bindings.json` indica las versiones de cada fuente. `planning.json` explica el origen de las URLs y los avisos de cobertura.

Revisa `planned_url_count`, `policy_excluded`, `code_errors` y `warnings`. Una URL propuesta todavía puede devolver 404, fallar por red o aportar únicamente contexto. El aviso de pocas fuentes de cambios indica que conviene ampliar las URLs revisadas antes de interpretar la cobertura. Las URLs adicionales deben incluirse en el `allowed_urls` del catálogo de entrada antes de volver a planificar. Para PRs y comparaciones fijadas por revisiones, declara sus versiones en `source_bindings` por URL.

### 5. Ejecutar el flujo completo

```powershell
& .\.venv\Scripts\python.exe -m r2 run "$modulo" --module-name $nombreModulo --from $origen --to $destino --plan "$plan/plan.json" --catalog "$plan/catalog.json" --bindings "$plan/bindings.json" --output-dir "$salida"
if ($LASTEXITCODE -ne 0) { throw "Revisa el error de ejecución" }
```

Este comando descarga, normaliza, guarda SQLite, cruza el módulo, extrae relaciones y escribe el reporte. Requiere acceso HTTPS a las fuentes. Cada ejecución necesita una carpeta de salida nueva. Conserva la ruta de `$salida` para volver a consultar la colección.

También puedes omitir `--plan` y `--bindings` para que `run` prepare el plan automáticamente. En ese caso usa el catálogo de entrada y una salida nueva. La ejecución guardará el plan en `planning/`.

### 6. Leer el reporte y comprobar las capturas

```powershell
Get-Content -LiteralPath "$salida/report.txt" -Encoding utf8
& .\.venv\Scripts\python.exe -m r2 validate-output "$salida/report.json"
Get-ChildItem -LiteralPath "$salida/temp_data" -Filter inventory.json -Recurse |
    ForEach-Object { Get-Content -LiteralPath $_.FullName -Encoding utf8 }
```

La salida contiene:

| Archivo | Contenido |
|---|---|
| `collection.sqlite` | Fuentes, originales retenidos, unidades e índices de búsqueda. |
| `crossing.json` | Coincidencias directas del módulo, evidencias y observaciones sin resolver. |
| `relations.json` | Unidades alcanzadas, relaciones y distancias desde las coincidencias. |
| `report.txt` y `report.json` | Candidatos de cambio, conteos, fuentes y advertencias. |
| `temp_data/<sesión>/inventory.json` | Estado de cada captura y motivo de fallos o exclusiones. |

`changes_found` cuenta los candidatos distintos recuperados. `changes_shown` cuenta los presentados, hasta diez. `eligible_distinct_changes` cuenta los bloques distintos que cumplen versión y capa. `new_findings_by_depth` indica cuántos llegaron por cruce directo o por saltos del grafo. Una relación expresa una identidad técnica compartida y cada candidato requiere revisar su aplicabilidad.

El reporte actual se consulta como texto y JSON. El dashboard visual de insights está pendiente. Si el resultado está vacío, revisa primero los estados de adquisición y los cambios elegibles. La falta de resultados puede deberse a fuentes fallidas, ausencia de diffs con versiones o ausencia de coincidencias técnicas.

### 7. Consultar de nuevo y comparar motores

Estos comandos reutilizan SQLite y permiten cambiar la profundidad o la capa.

```powershell
& .\.venv\Scripts\python.exe -m r2 query "$modulo" --module-name $nombreModulo --db "$salida/collection.sqlite" --from $origen --to $destino --depth 3 --limit 10
& .\.venv\Scripts\python.exe -m r2 query "$modulo" --module-name $nombreModulo --db "$salida/collection.sqlite" --from $origen --to $destino --layer python --depth 0 --format json
& .\.venv\Scripts\python.exe -m r2 query "$modulo" --module-name $nombreModulo --db "$salida/collection.sqlite" --from $origen --to $destino --engine bm25 --format json
```

La profundidad admite 0 a 3. Cero consulta coincidencias directas. El límite de diez se aplica al reporte y sus conteos conservan el total recuperado. BM25 permite comparar la recuperación léxica sobre el mismo corpus. La cantidad de resultados requiere contrastarse con su pertinencia.

### 8. Ejecutar las pruebas y consultar sus logs

```powershell
& .\.venv\Scripts\python.exe -m unittest discover -s tests -v
Get-Content -LiteralPath "audit/caja negra.log" -Encoding utf8
Get-Content -LiteralPath "audit/caja blanca.log" -Encoding utf8
```

Los dos logs incluidos registran la verificación de la entrega. Ejecutar `unittest` muestra resultados nuevos en la terminal. Las pruebas integrales usan respuestas HTTP controladas. La disponibilidad actual de las URLs se comprueba al ejecutar adquisición con red. La evaluación de tesis utiliza además referencias y juicios independientes, descritos en la sección Evaluación.

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
