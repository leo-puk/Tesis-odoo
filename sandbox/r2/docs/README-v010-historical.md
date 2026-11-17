# R2 Información local de migración de Odoo

R2 0.1.0 construye una colección SQLite desde diferencias de código/documentación y consulta un módulo original mediante análisis estático y relaciones. Funciona localmente sin IA, claves API, embeddings ni servicios de búsqueda externos. Los resúmenes son contadores; las explicaciones verificadas se incorporan como anotaciones explícitas de revisión.

Es un prototipo funcional de R2.1/R2.2. La colección de ejemplo contiene dos archivos del núcleo para 16→17; no equivale a una base completa 16–19 ni demuestra las metas de tesis. El backlog conserva el alcance implementado y pendiente.

## Usar la demostración existente en Windows

Desde esta carpeta:

```powershell
.\r2.ps1 query examples/original_module --db examples/output/verified-demo/reviewed.sqlite --from 16.0 --to 17.0 --status verified
.\r2.ps1 query examples/original_module --db examples/output/verified-demo/reviewed.sqlite --from 16.0 --to 17.0 --status verified --format json
.\r2.ps1 query examples/original_module --db examples/output/verified-demo/reviewed.sqlite --from 16.0 --to 17.0 --status verified --engine bm25
```

El lanzador usa .venv, R2_PYTHON o runtime.local.json. La configuración local identifica el Python 3.12 comprobado en este equipo y puede necesitar actualizarse si se actualiza Codex. No se instala nada en los directorios administrados del runtime. La salida declara graph_implementation: NetworkX si está disponible, o stdlib_bfs_fallback. La ruta local no es parte del paquete distribuible.

## Instalación independiente

Con Python 3.12 o posterior y Git:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
.\r2.ps1 --help
```

La instalación estándar incluye NetworkX y lxml. En un equipo sin acceso a paquetes, si Python ya tiene lxml, se puede ejecutar desde esta carpeta con `python -m r2`; el grafo usa un BFS alternativo de biblioteca estándar y lo declara en cada respuesta. No se presenta esa ejecución como uso de NetworkX. El entorno Docker probado inicialmente utilizó Python 3.12.15, NetworkX 3.7 y lxml 6.1.3. El runtime local probado utiliza Python 3.12.14 y el fallback de BFS. Las consultas no requieren Docker, PostgreSQL ni Odoo en ejecución.

## Arquitectura y métodos

1. **Recolección de fuentes**, collection.py: lee inventarios y árboles de repositorios Git locales o pares de directorios snapshot. Git resuelve ambos commits y lee blobs sin checkout ni ejecución. Los snapshots reciben una revisión SHA256 del conjunto y hashes por archivo; no se inventa un SHA Git para una imagen Docker.
2. **Extracción de información de migración**, extract.py y collection.py: ast lee declaraciones de modelos, clases, métodos, campos, decoradores y referencias explícitas; lxml/XPath lee vistas, QWeb, herencia y referencias XML; csv lee identificadores de seguridad; ast.literal_eval lee manifiestos declarativos. difflib genera bloques de comparación deterministas. Los mensajes MIG/FIX no definen cambios.
3. **Conversión de información**: cada bloque es candidato, con antes/después, rangos, elementos y fuente. Una revisión explícita puede confirmar, rechazar, restringir condiciones y agrupar varios bloques bajo un cambio semántico. No se deduce automáticamente que una diferencia rompe compatibilidad. Se conserva source_layer (archivo de evidencia) separada de layer (capa afectada revisada).
4. **Almacenamiento**: SQLite tiene metadata, sources, elements, relations, changes y el índice FTS5. Exportación JSON canónica. La construcción es atómica y no sobrescribe bases existentes. La revisión de colección incluye contenido, política y anotaciones; el tiempo de preparación queda fuera de esa identidad.
5. **Cruce**: identidades exactas de modelos, campos, métodos, identificadores externos, propiedades del API y atributos XML. Los atributos Python generales se califican por modelo para evitar emparejar indiscriminadamente cualquier browse o env de cualquier clase. Los símbolos de documentación son aproximaciones y permanecen candidatos salvo revisión.
6. **Extracción y recorrido de relaciones**, query.py/graph.py: grafo dirigido con relaciones por versión, fuente y ubicación. Se recorre con bfs_layers multiorigen o BFS alternativo. Cada nodo tiene profundidad mínima; los empates se resuelven lexicográficamente. Las semillas de consulta tienen profundidad 0. Las evidencias se adjuntan al elemento afectado sin añadir una distancia artificial por almacenar una cita.
7. **Filtro y ordenamiento**: filtro por salto, capa y estado, exclusión de rechazados y comprobación de required_elements. Primero verificados, menor distancia, mayor especificidad del elemento y más coincidencias; BM25 y el ID estable desempatan. Para un bloque revisado, affected_elements restringe el extremo del camino a los elementos realmente respaldados. Los parámetros están en código versionado; no se entrenan pesos.
8. **Presentación**: hasta diez cambios distintos y resumen de todos los encontrados dentro de la profundidad configurada. Texto en inglés o JSON schema_version=1; log JSONL opcional. La búsqueda y el resumen son deterministas. elapsed_seconds y las mediciones de preparación varían naturalmente entre ejecuciones.
9. **Comparación y evaluación**: FTS5 implementa BM25 sin expansión de relaciones. Ambos sistemas utilizan el mismo corpus de cambios y elementos iniciales. El evaluador separado recibe correspondencias y juicios humanos; los datos de referencia no alimentan el índice.

## Inventario de fuentes

El inventario es un array JSON. Las rutas se resuelven desde el archivo de inventario.

```json
[
  {
    "id": "core-16-17",
    "kind": "official_code",
    "split": "construction",
    "parent_ids": [],
    "format": "git",
    "repo": "C:/repos/odoo",
    "prefix": "odoo",
    "from_revision": "SHA_DEL_COMMIT_16",
    "to_revision": "SHA_DEL_COMMIT_17",
    "from_version": "16.0",
    "to_version": "17.0"
  }
]
```

Para snapshots, usar format=snapshot, before_dir y after_dir en lugar de repo/prefix/revisiones. Se pueden comparar snapshots de documentación oficial y guías también: los spans de código entre backticks proporcionan símbolos. No se descarga automáticamente todo Internet ni se consulta la API de GitHub en esta versión; primero se obtienen las fuentes y se fijan sus revisiones. La lectura Git admite repositorios bare, como los de la caché del laboratorio.

Kinds admitidos: official_code, official_documentation, oca_guidance, openupgrade_analysis, oca_migration, oca_fix, derived. Splits: construction y evaluation_reference. Cada fuente derivada debe indicar sus padres. La exactitud del etiquetado de procedencia es responsabilidad del inventario: el selector no detecta copias mal etiquetadas de soluciones reservadas.

```powershell
.\r2.ps1 build inventory.json --db collection.sqlite --no-include-oca-migrations
```

--no-include-oca-migrations es el valor predeterminado. --include-oca-migrations permite exclusivamente fuentes de construcción; las soluciones evaluation_reference y sus derivados quedan excluidos siempre. Si cambia la política se construye otra base. La consulta rechaza una colección cuyo modo no coincide con el solicitado.

## Revisión y agrupación de cambios

Construir candidatos, exportarlos y revisar:

```powershell
.\r2.ps1 export --db collection.sqlite > collection.json
.\r2.ps1 show --db collection.sqlite chg_ID
.\r2.ps1 build inventory.json --annotations review.json --db reviewed.sqlite
```

Un archivo review.json contiene un array:

```json
[
  {
    "change_id": "chg_ID_REAL_DE_LA_BASE",
    "status": "verified",
    "title": "English description supported by the diff",
    "reviewer": "Identified reviewer",
    "rationale": "Explanation of why the evidence supports this interpretation",
    "required_elements": ["property:states"],
    "affected_elements": ["property:states"],
    "layer": "python"
  }
]
```

required_elements es una condición sobre los elementos presentes en la consulta original. affected_elements debe ser un subconjunto de los elementos identificados en el bloque. No se permite añadir una evidencia inexistente mediante una anotación.

Para agrupar varios bloques, asignarles el mismo group_id y el mismo título, salto, estado verified y capa principal. El programa produce un grp-ID y conserva todos los evidence_blocks. Cada cambio se cuenta una vez; sus bloques no se vuelven a contar. Si una adaptación afecta varias capas, la revisión asigna una capa principal; los archivos y source_layer de todas las evidencias se conservan.

El ejemplo run_demo.py incorpora dos revisiones de desarrollo explícitas sobre código del núcleo. No son juicios independientes de pertinencia ni resultados de evaluación de tesis.

## Consulta y contrato JSON

```powershell
.\r2.ps1 scan C:/addons/my_module
.\r2.ps1 query C:/addons/my_module --db reviewed.sqlite --from 16.0 --to 17.0 --layer xml --depth 3 --status verified --format json --log queries.jsonl
.\r2.ps1 inventory --db reviewed.sqlite
.\r2.ps1 validate-output query.json
```

Comandos disponibles: build, scan, query, inventory, export, show, validate-output, evaluate. `query --engine bm25` ejecuta la referencia léxica. `--limit` admite de 1 a 10 y `--depth` de 0 a 20. Los saltos no consecutivos muestran cambios intermedios existentes en la base, cotejados contra el código original; no simulan haber transformado cada versión intermedia.

Cada resultado conserva ID, versiones y revisiones, capa afectada, capa del archivo de evidencia, fuente, archivo, rangos antes/después, texto del diff, estado, elementos, condiciones, profundidad y camino con evidencia por relación. Los grupos conservan las evidencias completas. BM25 declara profundidad nula y camino vacío, porque no realiza recorrido estructural; no se le atribuye una trazabilidad de grafo que no produjo.

Resumen: changes_found, changes_shown, matching_migrations, methods_with_documented_changes, changes_by_layer y new_findings_by_depth. Los métodos contados son identidades de los elementos encontrados en los cambios, no la cantidad de métodos distintos del módulo que necesariamente haya que editar. Si MIG está desactivado, matching_migrations vale cero. Un candidato mostrado no se convierte por ello en incompatibilidad confirmada.

La validación V1 comprueba campos estructurales, caminos, unicidad, límite y contadores; no juzga la pertinencia semántica ni traduce textos libres. Las etiquetas y mensajes del programa están en inglés. Los títulos revisados deben redactarse en inglés; los fragmentos originales se conservan literalmente.

## BM25

SQLite FTS5, tokenizador unicode61, k1=1.2 y b=0.75. Antes de indexar se separan identificadores en secuencias [A-Za-z_][A-Za-z_0-9]*; se conservan frecuencias en documentos. La consulta usa los términos únicos ordenados de los elementos del módulo, unidos mediante OR. Una puntuación menor es mejor. El baseline aplica los mismos filtros y unidad de cambio, sin añadir términos del grafo ni caminos. Su evaluación necesita juicios de pertinencia; no se presume superioridad de ninguno de los dos motores.

## Evaluación de la tesis

evaluate recibe un JSON independiente con reviewer, references y queries. Cada referencia evaluable necesita id, module, jump, justification y covered_by (IDs de cambios existentes). Cada consulta necesita id, module, versiones, reference_ids y judgments por resultado. Cada juicio requiere relevant booleano, justification y reference_ids cubiertos por ese resultado. Las rutas de módulos se resuelven desde el JSON de evaluación.

```json
{
  "reviewer": "Nombre del evaluador independiente",
  "cache_state": "uncontrolled",
  "references": [
    {"id": "ref1", "module": "module_name", "jump": "16.0->17.0", "evaluable": true,
     "justification": "Juicio explícito de cobertura", "covered_by": ["chg_ID"]}
  ],
  "queries": [
    {"id": "q1", "module": "../module_name", "from_version": "16.0", "to_version": "17.0",
     "reference_ids": ["ref1"],
     "judgments": {"chg_ID": {"relevant": true, "justification": "Aplicabilidad contrastada", "reference_ids": ["ref1"]}}}
  ]
}
```

```powershell
.\r2.ps1 evaluate evaluation.json --db collection.sqlite --repeats 3 > metrics.json
```

El evaluador exige juicio para cada resultado mostrado por ambos motores; si faltan, se detiene e informa los IDs. No rellena pertinencia con IA ni trata la ausencia de juicio como irrelevancia.

- C1: porcentaje de referencias evaluables cubiertas por la base según los juicios de cobertura; desglose módulo/salto.
- P1: pertinentes / entregados en la primera vista. Vacío: null.
- C2: referencias pertinentes explicadas / referencias pertinentes de la consulta. Sin referencias: null. Si hay referencias pero ninguna respuesta: 0.
- V1: proporción de ejecuciones con contrato conforme.
- T1: análisis y producción de primera vista estructurada y resumen; tiempos individuales, mediana, repeticiones, entorno y caché declarada. Construcción se informa aparte. No incluye latencia de impresión del terminal.

Se reportan medias macro de consultas definidas, vacíos, diferencia descriptiva P1 contra BM25 y unión de cambios cubiertos por módulo. No se aplican por defecto McNemar, Wilson ni pruebas de superioridad a resultados dependientes. Esta versión usa json/csv y statistics estándar en vez de pandas, scikit-learn o statsmodels; esas decisiones están declaradas en el backlog.

## Verificación y límites

```powershell
# Con el Python indicado en R2_PYTHON o el entorno virtual:
python -m unittest discover -s tests -v
python -m examples.run_demo --output examples/output/new-demo
```

El directorio de salida de una nueva demostración debe ser nuevo: no se sobrescriben bases. El ejemplo usa fuentes locales y el módulo original como entrada de lectura. No migra el módulo ni altera la tesis.

Pruebas: flujo completo, estabilidad de revisión de colección, capas y versiones, caminos, profundidad mínima, ciclos, límite diez, contadores, exclusión y política, evaluación vacía y con juicios, rechazo de XML DTD, sintaxis inválida, no ejecución del código de entrada, anotaciones y agrupación semántica.

Límites: no hay inferencia completa de tipos, MRO del registro Odoo, referencias dinámicas, arquitectura XML final ni correspondencias automáticas perfectas entre todas las APIs. Los símbolos generales pueden producir candidatos irrelevantes. Los renombrados de archivos Git se observan como baja/alta de rutas; no se reconstruye automáticamente su identidad semántica. Las fuentes oficiales completas, API GitHub, revisión del corpus, calibración del orden y evaluación independiente de treinta migraciones quedan pendientes. JavaScript/Owl permanece fuera de alcance según la tesis. La verificación funcional y la transformación son R3 y R4.
