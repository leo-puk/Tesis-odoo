# Integración del componente final de adquisición

El componente final está en `r2/adquisition`. Sus archivos se copiaron sin modificar desde la entrega del usuario, conservada en `reference/adquisition-final`. La versión anterior quedó en `archive/adquisition-v020`. Investigación y archivos OpenUpgrade de la referencia no son fuentes del corpus ni se recorren durante la construcción.

## Flujo implementado

Plan y catálogo → adquisición → inventario por sesión → `ingestion` → `conversion` → colección SQLite de esquema 3 → consulta estructural o BM25. El componente final también conserva su CLI independiente: `python -m r2.adquisition`.

- `r2/ingestion/session.py` lee solamente unidades `accepted`. Valida rutas, enlaces, estados y bindings externos. Lee únicamente los archivos enumerados por la unidad. No hace peticiones HTTP ni modifica el inventario.
- `r2/conversion/diff.py` interpreta hunks textuales, rangos y rutas de archivos nuevos/eliminados. Rechaza conteos incompletos, contenido sobrante y rutas inseguras. Metadatos de renombrado y diferencias binarias permanecen en los artefactos sin generar cambios textuales inventados. La sintaxis combinada y algunas rutas escapadas no están soportadas y se rechazan explícitamente.
- `r2/conversion/units.py` extrae candidatos exclusivamente de diffs directos o del campo `diff` de un PR. Los comentarios y revisiones completos permanecen en el artefacto JSON, sin aumentar los contadores de cambios. Documentación y manifiestos se guardan como contexto. El manifiesto se interpreta estáticamente como `__manifest__.py` aunque adquisición lo haya almacenado como TXT.
- `collection.build_session()` guarda artefactos completos, documentos contextuales, fuentes, elementos, relaciones, comparaciones, evidencias y cambios. No sobrescribe colecciones existentes ni elimina temporales.
- `query` conserva citas de sesión/unidad, ofrece los documentos enlazados explícitamente y admite esquema 2 histórico y esquema 3 actual. Los resultados y las relaciones extraídos de hunks se identifican como parciales.
- `evaluation_sources` conserva el cliente de metadatos limitados para selección académica. No usa la captura completa de PR ni introduce expedientes de evaluación en la colección de construcción.

## Bindings del procesamiento

Adquisición no asigna versiones. El consumidor exige un archivo externo con `sources`, cuyas claves son el `source_id` original del plan o el ID de unidad. Cada entrada declara `from_version` y `to_version`. Para diffs y PR también declara `from_revision` y `to_revision` como referencias de comparación, sin afirmar que sean SHA inmutables.

`context_units` enlaza explícitamente documentos por ID de unidad o por ID original del plan. La relación se valida dentro de la sesión y se rechazan unidades ausentes, excluidas o de tipo diff/PR como documentos contextuales. `module` es opcional y permite conservar la identidad técnica de un manifiesto o un fragmento interpretable.

Ejemplo: `examples/session-bindings.json` corresponde al plan final de referencia. Las comparaciones de GitHub mantienen la semántica del endpoint compare que usa el componente final; sus hunks no acreditan una comparación de todos los archivos completos de dos ramas.

## Procedencia y conservación

La ingestión calcula un SHA256 de cada archivo almacenado que consume, fuera de adquisición. Su alcance queda explícito: identifica ese artefacto, no el cuerpo HTTP original. El inventario final no se modifica para añadir hashes. HTML convertido no equivale al original HTML y no permite reconstruirlo.

Las fechas, URLs e identificadores de captura se conservan en `sources`; los textos completos de artefactos se conservan en SQLite. Una vez construida y comprobada la colección, se pueden eliminar las unidades mediante `delete-units`. La consulta ya no depende de esos temporales. No hay eliminación automática ni protección inventada frente a una edición anterior a la primera ingestión.

## Política y compatibilidad

Los comandos activos no ofrecen el interruptor OCA. Las antiguas llamadas Python que intenten activarlo fallan expresamente. La política fija del componente final sigue dependiendo del catálogo revisado y no se presenta como garantía absoluta de ausencia de filtraciones.

`build` exige inventario final y bindings. `build-legacy` identifica explícitamente la reconstrucción local histórica de Git/snapshots, con exclusión fija de MIG/FIX OCA y derivados. No es una nueva admisión mediante catálogo. Su metadata distingue `historical_local_import` de `final_catalog_admitted_units_v1`. No transforma automáticamente una colección antigua en esquema 3 ni reescribe las bases existentes.

`r2/acquire.py` solo reexporta la API pública final. No se mantienen equivalencias falsas para las antiguas funciones de búsqueda, hashes o firmas incompatibles. Los consumidores de evaluación se actualizaron a `evaluation_sources`. Las referencias temporales finales son datos de una sesión: dos capturas nuevas tienen IDs distintos, aunque soliciten las mismas URLs.

## Validación y límites

La suite integra las 21 pruebas originales finales mediante un adaptador externo de importaciones. No se editó el componente ni esas pruebas. Se conservan pruebas de regresión del motor anterior y se añaden pruebas de captura/CLI/construcción/consulta/exportación/borrado, PR JSON, documentos contextuales, manifiestos, versiones, rangos, diffs truncados y rutas inseguras.

Los tests usan respuestas simuladas. No se realizó una captura real de producción ni se completó el catálogo. El catálogo de referencia tiene `allowed_urls` vacío intencionalmente. Las pruebas sintéticas no acreditan precisión, cobertura o equivalencia funcional de migraciones reales.

No se reconstruyen archivos completos a partir de hunks. Un fragmento sin anclas interpretables se conserva, pero puede no recuperarse por grafo; BM25 puede encontrarlo si coincide lexicalmente. La ausencia de resultado no prueba ausencia de impacto. La revisión humana puede agrupar/dividir evidencias con el contrato de anotaciones existente; no se declara equivalencia semántica automática entre unidades capturadas distintas.

Las colecciones nuevas no se marcan automáticamente como académicamente auditadas por tener estado `accepted`. La evaluación de ingeniería funciona con `--development`; la evaluación final continúa protegida por selección, responsables, juicios y protocolo. Para habilitar una evaluación académica del corpus nuevo se necesitará su auditoría independiente y conexión explícita con el registro de asignaciones; no se inventó esa aprobación durante esta integración.

Los informes y hashes previos de `audit` identifican entregas anteriores. La integridad del componente final se registra aparte en `audit/adquisition-final-baseline.json` y se verifica mediante pruebas.


## Comprobación funcional posterior con código OCA real

Se añadió `examples/run_oca_functional_test.py` y su regresión automatizada. Usa la copia local sin modificar de sale_advance_payment 16.0.1.0.0 como entrada de consulta 16→17. La respuesta HTTP se simula con un diff calculado entre los dos snapshots locales reales de fields.py e ir_ui_view.py. No se consulta una solución MIG/FIX de OCA ni se descarga un PR real.

La prueba detectó que los hunks incompletos podían perder anclas al depender solo del AST. Se agregó `conversion/anchors.py`: inspecciona tokens locales para propiedades de la API de campos en sus rutas conocidas y atributos literales de llamadas xpath. No reconstruye clases, ejecuta código ni infiere dueños o relaciones a partir de esos tokens. Sus ocurrencias registran extraction_basis y alcance hunk_only. Se comprueba también que comentarios, cadenas de texto y xpath dinámicos no generen esas anclas. El componente final de adquisición no se modificó.

Para reproducir: `.venv\Scripts\python.exe -m examples.run_oca_functional_test --output examples/output/oca-functional-otra-ejecucion`. La salida debe ser nueva. Los detalles y límites están en [la prueba funcional](../audit/OCA_FUNCIONAL_16_17.md).
