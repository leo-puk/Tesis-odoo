# Reauditoría de Acquisition con alcance aclarado

17 de noviembre de 2026. Sustituye las conclusiones de alcance de la auditoría anterior, conservando sus evidencias. La exploración y las relaciones semánticas con el módulo del partner pertenecen a otro componente. No se consideran capacidades faltantes de Acquisition.

## Alcance y dictamen

Acquisition obtiene el contenido completo de las unidades indicadas en el plan y admitidas por el catálogo, con múltiples orígenes. En esta repetición se usaron HTTPS reales: no hubo mocks de red en las descargas de fuentes. Se procesaron catorce entradas, además de un caso CLI separado. No se usaron ingestion, SQLite, grafo, extracción de cambios ni evaluación del módulo.

El flujo de descarga, admisión, almacenamiento, metadatos, caché y borrado funcionó en los casos ejecutados; las 21 pruebas originales del componente volvieron a pasar. Sigue existiendo un defecto reproducible de manejo de charset que puede abortar el lote. El filtro literal puede rechazar documentos oficiales por coincidencias de palabras. Esos resultados impiden afirmar funcionamiento integral para cualquier fuente.

El término “todo” se verificó como contenido completo de los archivos/documentos configurados, no como clonación completa de repositorios u organizaciones. No se clonó Odoo, OCA ni OpenUpgrade. El código actual sigue aplicando el catálogo antes de persistir: no guarda para otro componente los cuerpos que haya excluido. Si se desea preservar también esos cuerpos y posponer todo filtrado, sería un cambio respecto al comportamiento final vigente.

## Fuentes reales guardadas y URLs

| Unidad | URL del plan | Tamaño guardado |
|---|---|---|
| odoo-doc-text | https://raw.githubusercontent.com/odoo/documentation/17.0/content/developer/reference/backend/orm/changelog.rst | 4040 bytes |
| odoo-manifest | https://raw.githubusercontent.com/odoo/odoo/17.0/addons/sale/__manifest__.py | 3180 bytes |
| odoo-diff | https://github.com/odoo/odoo/compare/6d6e53dc20a506af2bb5dd25e2360c13d024a0eb...cdaa761cedf657614c30c3d8b146054812daf3fe | 158315 bytes |
| oca-tools | https://raw.githubusercontent.com/wiki/OCA/maintainer-tools/Migration-to-version-17.0.md | 8604 bytes |
| openupgrade-crm-script | https://raw.githubusercontent.com/OCA/OpenUpgrade/17.0/openupgrade_scripts/scripts/crm/17.0.1.8/pre-migration.py | 806 bytes |
| oca-tools-merged-pr | https://github.com/OCA/maintainer-tools/pull/684 | 30079 bytes |

El PR OCA/maintainer-tools#684 se obtuvo mediante siete consultas de recursos: PR, archivos, commits, comentarios, revisiones, comentarios de revisión y diff. Se guardó descripción, un archivo, un commit, un comentario y una revisión; no había comentarios de revisión. Los listados coincidieron con los contadores del PR. Los endpoints y parámetros reales están en network.jsonl.

Para RST, manifiesto, diff, guía y script CRM coincidieron los tamaños recibidos y guardados, sin resumen o selección de bloques. Esta comprobación no demuestra por sí sola cobertura de un repositorio completo. El JSON agregado del PR es una representación compuesta de los recursos consultados y no se compara por longitud con un único cuerpo HTTP.

## Descargadas pero excluidas

- odoo-doc-html: https://www.odoo.com/documentation/17.0/developer/reference/backend/orm.html — OCA addon identifier detected; entire unit excluded.
- openupgrade-doc: https://oca.github.io/OpenUpgrade/070_migration_files.html — OCA addon identifier detected; entire unit excluded.
- openupgrade-mixed-script: https://raw.githubusercontent.com/OCA/OpenUpgrade/16.0/openupgrade_scripts/scripts/base/16.0.1.3/pre-migration.py — OCA addon identifier detected; entire unit excluded.
- mixed-before-network: https://raw.githubusercontent.com/odoo/documentation/17.0/content/developer/reference/backend/orm/changelog.rst — OCA addon identifier detected; entire unit excluded.

La documentación ORM oficial fue excluida por la palabra knowledge. La página de OpenUpgrade coincidió con knowledge y OCA/account-invoicing; el script base coincidió con tres identificadores OCA del catálogo. No se conservaron sus cuerpos. El PR Odoo #95589 no tenía merged_at y se rechazó conforme a la regla actual. Los controles del addon objetivo, mezcla con URL excluida y URL sin revisar se rechazaron antes de la red.

## Qué son unidad y hunk

- **Unidad de Acquisition:** una entrada del plan, identificada por id. Puede contener un documento/archivo o agrupar varios enlaces en files. Se admite, guarda o descarta el grupo entero. Un PR completo es una unidad aunque contenga datos de muchos archivos.
- **Hunk:** un bloque de líneas modificadas dentro de un diff, delimitado por una cabecera @@. Un diff completo puede contener varios archivos y muchos hunks. Un hunk no equivale necesariamente a un cambio semántico.

Ejemplo: una entrada que descarga core.diff es una unidad. Ese archivo puede incluir cambios de fields.py e ir_ui_view.py y numerosos bloques @@. Acquisition conserva el diff entero y no interpreta ni recorta esos bloques. La exploración posterior puede hacerlo en su propio componente.

## Investigación de LookupError

La cabecera HTTP Content-Type puede indicar la codificación: por ejemplo text/plain; charset=utf-8. document_text extrae ese nombre y llama raw.decode(nombre). Si el nombre no está registrado en Python, bytes.decode lanza LookupError; no es el mismo caso que un archivo con bytes inválidos para UTF-8. Un codec conocido pero no textual, como rot_13, también provoca LookupError en bytes.decode.

Ruta comprobada: documents.py:35 → sources.py:95 → el except de sources.py:116 no captura LookupError. Ese except solo contempla ValueError, OSError y UnicodeError. LookupError hereda directamente de Exception; UnicodeDecodeError hereda de UnicodeError y ValueError. Por ello los bytes UTF-8 inválidos sí se registran como failed y la ejecución continúa, pero un nombre de codec desconocido se escapa.

| Caso controlado | Resultado observado |
|---|---|
| UTF-8 correcto | Decodifica |
| ISO-8859-1 correctamente declarado | Decodifica |
| Sin charset, contenido UTF-8 | Decodifica usando UTF-8 |
| Codec desconocido en la primera unidad | LookupError; no se solicitan las siguientes; no se alcanza a crear inventario/log de esa sesión |
| Codec desconocido en la segunda unidad | Se conserva la primera unidad y su inventario/log; se aborta sin solicitar la tercera y no hay evento finished |
| Bytes inválidos para UTF-8 en la segunda unidad | Estados accepted, failed, accepted; el lote finaliza |
| Codec rot_13 en la segunda unidad | LookupError y aborto, igual que el nombre desconocido |

Incluso errors="replace" sigue produciendo LookupError para un codec inexistente: ese parámetro no instala ni identifica codificaciones. No ocurrió este error en las URLs reales de esta repetición; se reprodujo mediante respuestas controladas HTTP 200 con cabeceras deliberadamente problemáticas. Es un defecto latente del conversor/manejo de errores, no una prueba de que GitHub haya fallado.

Corrección mínima propuesta, sin aplicarla: capturar LookupError exclusivamente alrededor de la decodificación y convertirlo en un ValueError descriptivo (o una excepción documental específica que capture el coordinador). Así la unidad queda failed y se continúa. No conviene adivinar otra codificación silenciosamente ni usar except Exception indiscriminadamente. El test de regresión debe exigir accepted, failed, accepted y un evento finished.

Fuentes técnicas: [Registro de codecs de Python 3.12](https://docs.python.org/3.12/library/codecs.html#codecs.lookup), [Jerarquía de excepciones](https://docs.python.org/3.12/library/exceptions.html#LookupError), [bytes.decode](https://docs.python.org/3.12/library/stdtypes.html#bytes.decode).

## Evidencias y conservación

- [live-report.json](../temp_data/acquisition-reaudit-20261117/live-report.json): repetición real y verificaciones de caché/borrado/CLI.
- [network.jsonl](../temp_data/acquisition-reaudit-20261117/network.jsonl): URL exacta, estado, tamaño y fecha de cada respuesta real.
- [content-completeness-checks.json](../temp_data/acquisition-reaudit-20261117/content-completeness-checks.json): tamaños de cuerpos y archivos.
- [charset-investigation.json](../temp_data/acquisition-reaudit-20261117/charset-investigation.json): casos, tracebacks y efectos sobre el plan.
- [component-tests.txt](../temp_data/acquisition-reaudit-20261117/component-tests.txt): 21 pruebas originales aprobadas.
- [plan.json](../temp_data/acquisition-reaudit-20261117/plan.json) y [catalog.json](../temp_data/acquisition-reaudit-20261117/catalog.json): configuración de esta ejecución.

Los archivos y trazas grandes están en temp_data, ignorado por Git. El componente final conserva sus nueve archivos originales. No se alteró el backlog, no se cambió su política ni se publicó nada en GitHub.
