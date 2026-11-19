# Cruce inicial de identificadores

`crossing` lee código del partner y localiza coincidencias técnicas directas en una colección normalizada. Entrega IDs de unidades y evidencias puntuales al siguiente componente. El contenido completo permanece en SQLite.

No ejecuta código, descarga fuentes, crea relaciones entre unidades, expande grafos, utiliza ranking, decide incompatibilidad ni aplica arreglos. BM25, TF-IDF y embeddings no intervienen en las coincidencias. No filtra versiones: conserva la identidad de la colección utilizada.

## Entradas

- `database`: colección SQLite, esquema 4, generada con las reglas actuales `normalization-3`. Requiere `information_units`, `unit_entities`, `sources` y el índice `unit_entity_lookup`. La conexión es de solo lectura.
- `module`: archivo individual o carpeta. Se conserva el nombre de argumento anterior por compatibilidad con `cross_module(database, module, ...)` y la CLI.
- `module_name`: nombre técnico explícito del addon, opcional. No se deduce de la carpeta, archivo ni nombre visible del manifiesto.
- `output`: ruta opcional de un JSON nuevo. Nunca se sobrescribe un archivo existente ni la colección.

Formatos: Python, XML, CSV y manifiestos literales `__manifest__.py`. Una carpeta se recorre sin seguir symlinks/junctions ni entornos/cachés. Un archivo individual no provoca lectura de sus vecinos. Una entrada inexistente y un formato no soportado producen errores diferentes.

`input.module_path` sigue disponible: contiene la ruta de la entrada, que ahora también puede ser un archivo. Se añaden `input.input_path` y `input.input_kind` (`file`/`directory`). Los localizadores de un archivo individual usan su nombre relativo a la entrada, sin inferir la raíz técnica del addon.

## Salida y entrega por IDs

Versión de salida: **2**. Reglas de cruce: **crossing-2**. Campos principales:

| Campo | Contenido |
|---|---|
| `collection` | Revisión, esquema y reglas de normalización utilizados. |
| `input` | Identificación de la entrada, archivos leídos, observaciones, errores y limitaciones. No contiene código fuente completo. |
| `matched_unit_ids` | IDs ordenados, únicos y coherentes con `results`. |
| `results` | Solo `information_unit_id` y `evidences` por unidad. |
| `evidences` | Observación del partner y de la unidad, localizadores, tipo, ámbito, origen, reglas de extracción e identidad/regla del cruce. |
| `unresolved` | Observaciones del partner que no pueden formar una identidad técnica elegible y su motivo. |
| `rejected_candidates` | Observaciones candidatas rechazadas por tipo/ámbito/namespace, sin documento completo. |
| `summary` | Contadores de archivos, observaciones, unidades y evidencias. |
| `result_id` | Identidad reproducible del informe, sin fecha ni tiempo variable. |

No se incluye `unit` ni se copian `text`, `data`, `terms` o todas las entidades de un documento. `validate_result()` comprueba la coherencia de IDs, evidencias y contadores antes de devolver o guardar el informe. El consumidor posterior recibe `matched_unit_ids` y puede recuperar esas unidades de la misma revisión de colección; ese componente no está implementado aquí.

Extracto ilustrativo de salida con coincidencia —el JSON real incluye el resto del contrato—:

```json
{
  "matched_unit_ids": ["unit-ejemplo"],
  "results": [{
    "information_unit_id": "unit-ejemplo",
    "evidences": [{
      "match_rule": "exact_typed_scoped_identity_v1",
      "identity": ["method", "res.partner", "action"],
      "input_entity": {"name": "action", "type": "method", "location": {"artifact_path": "partner.py", "content_line": 3}},
      "unit_entity": {"name": "action", "type": "method", "location": {"artifact_path": "captura/model.py", "content_line": 3}}
    }]
  }]
}
```

Sin coincidencias, `matched_unit_ids` y `results` son listas vacías, con contadores cero. Los errores y referencias no resueltas siguen presentes: vacío no significa migración correcta.

## Elegibilidad y reglas

Se separan dos decisiones:

1. **Partner:** solo observaciones de instrucciones de código son semillas. Comentarios, cadenas arbitrarias y menciones entre backticks no generan modelos, campos ni métodos.
2. **Unidad:** puede cruzar una observación de código, documentación o comentario si su tipo técnico y los datos de ámbito requeridos están explícitos. `identifier_mention` sigue sin ser una identidad técnica; su escritura o `lookup_keys` no bastan para reinterpretarla.

La regla de identidad es sensible a mayúsculas y conserva puntos y guiones bajos. Se mantienen las familias anteriores:

| Familia | Condición |
|---|---|
| Métodos / referencias de método | Nombre exacto y mismo modelo propietario conocido. |
| Campos / referencias de campo / rutas de campo | Familia compatible, nombre exacto y propietario conocido. |
| Funciones y clases Python | Namespace de addon explícito, archivo técnico y nombre cualificado/ámbito compatibles. Las funciones locales no se convierten en métodos ni funciones globales. |
| Identificadores externos | Namespace exacto. Los locales requieren módulo explícito; no se adivina. |
| Rutas y claves de manifiesto | Namespace de addon conocido y nombre exacto. |
| Modelos, módulos, opciones de campo, atributos XML, expresiones XPath | Tipo e identificador exactos conforme a las reglas ya reconocidas. |

El candidato se obtiene mediante el índice `(name,type)`; después se verifica su ámbito. Las entidades del índice deben coincidir con la entidad/ordinal almacenados en su unidad. Una fila inconsistente exige reconstrucción de la colección.

Una coincidencia documental o en comentario **no valida la afirmación que contiene**. Actualmente normalization solo produce menciones genéricas para muchos documentos y comentarios: esos casos no cruzan. La elegibilidad de entidades documentales tipadas se prueba aisladamente, sin fabricar una colección normalizada que el extractor actual no podría generar.

## CSV explícito en ambos lados

Se revisó el extractor CSV histórico, hoy ubicado en `r2/extract_relations/core.py`: sus convenciones `id`/`:id` son pertinentes, pero también genera relaciones de seguridad, fuera de este alcance. Se conserva intacto y se comparte una extracción pura en `r2/csv_entities.py`, usada por los extractores corregidos de normalización y por el lector de crossing.

- Solo `id` y columnas terminadas en `:id` producen observaciones `external_id`.
- Se conservan fila lógica, inicio/fin de líneas físicas, número/nombre de columna y valor original.
- `base.group_user` conserva su namespace; `local_id` requiere `module_name` o módulo explícito de la fuente.
- `base.model_res_partner` sigue siendo un XML-ID. Nunca se convierte en el modelo `res.partner`.
- Números, descripciones y columnas arbitrarias no generan identificadores.
- Filas con distinto número de columnas, identificadores inválidos o errores de comillas generan limitaciones explícitas. Las referencias con listas o formatos no soportados no se reinterpretan.
- Un fragmento de diff CSV sin cabecera verificable al comienzo del archivo no recibe una cabecera inventada.
- No se crean relaciones de seguridad ni conexiones entre unidades.

El ajuste autorizado de normalización se limita a llamar a este extractor y versionar las reglas como `normalization-3`. Es necesario reconstruir una colección nueva desde las capturas para indexar estas entidades; no se sobrescriben fuentes ni bases existentes.

## Uso

Desde la raíz del proyecto:

```powershell
.\r2.ps1 cross RUTA_ARCHIVO_O_CARPETA --db COLECCION.sqlite --module-name nombre_addon --output cruce.json
.\.venv\Scripts\python.exe -B -m examples.run_crossing_demo --output temp_data/otro-ejemplo-cruce
```

API:

```python
from r2.crossing import cross_module, save_result

result = cross_module("collection.sqlite", "partner.py", module_name="demo")
ids = result["matched_unit_ids"]
save_result(result, "cruce.json")
```

`examples/crossing-results.json` conserva ejemplos completos con y sin coincidencias, producidos por la demo con HTTP simulado. No son una descarga real ni evaluación académica.

## Errores y límites

`status` diferencia `complete`/`partial`. `outcome` diferencia `matches`, `no_matches`, `no_resolvable_identifiers` y `undetermined`. Los fallos por archivo se registran, sin dejar de analizar otros archivos válidos. Una entrada o colección inválida provoca una excepción explícita y un error de CLI, nunca un informe de ausencia de coincidencias.

`no_matches` describe las identidades elegibles analizadas. Si el informe es parcial, no acredita ausencia global. Los propietarios, namespaces o referencias dinámicas no demostrables permanecen desconocidos. Para archivos individuales puede faltar la ruta relativa al addon necesaria para cruzar funciones Python globales; no se deduce del entorno.

## Pruebas y backlog

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_crossing*.py" -v
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Las regresiones nuevas están en `tests/test_crossing_corrections.py`: ausencia de copias de unidades, coherencia del informe, elegibilidad por lado, archivo individual, CSV real en ambos lados, coordenadas, errores y CLI/persistencia. La prueba del guard de archivo enlazado es portable y simula `is_symlink`, porque crear symlinks reales puede requerir privilegios en Windows; no se presenta como una prueba de creación real de enlaces.

El backlog original C01–C15, su cruce de evidencia y los resultados ejecutados se mantienen en [CONTEXTO_PROYECTO.md](../../CONTEXTO_PROYECTO.md). Este README documenta el contrato solicitado; su mera existencia no sustituye pruebas de comportamiento ni amplía requisitos.
