# Backlog aprobado e implementación de acquisition

Esta es la especificación vigente. Sustituye las propuestas anteriores sobre interruptores, hashes, normalización completa y chunks. El nombre del paquete existente se conserva: adquisition.

## Contrato

Recibe un plan de enlaces y un catálogo de admisión. Guarda unidades completas aceptadas dentro de temp_data/<session_id>/<unit_id>. No descubre fuentes, descarga repositorios enteros, analiza el código del partner, puntúa relevancia, resume, crea chunks ni aplica arreglos. Otro componente comprime y extrae lo importante.

Una entrada del plan agrupa los archivos asociados a una unidad; cualquier coincidencia excluye la entrada completa. Cada entrada requiere id, kind y files. No se admite before/after. Los tipos son official_manifest, official_documentation, oca_guidance, openupgrade_analysis, github_diff y github_pr.

## Backlog y estado

| ID | Especificación | Estado |
|---|---|---|
| A01 | Validar esquema del plan, IDs únicos y catálogo obligatorio | Implementado |
| A02 | Conservar unidades completas, sin fragmentación ni resumen | Implementado |
| A03 | Guardar capturas únicamente en temp_data por sesión e ID | Implementado |
| A04 | Descargar manifiestos explícitos, nunca todo el código oficial | Implementado |
| A05 | Descargar documentación; convertir HTML y texto a TXT/MD | Implementado para formatos textuales |
| A06 | Obtener diffs de odoo/odoo mediante GitHub REST | Implementado |
| A07 | Admitir solamente enlaces exactos presentes en el catálogo | Implementado |
| A08 | Excluir repositorios e identificadores de addons OCA catalogados | Implementado |
| A09 | Excluir completas las unidades mixtas detectadas | Implementado por reglas determinísticas |
| A10 | Política fija, sin interruptor ni splits de evaluación | Implementado |
| A11 | PR fusionados: descripción, diff, archivos, commits, comentarios y revisiones | Implementado |
| A12 | ID simple, URL, fecha, estado y ubicación; sin hashes calculados | Implementado |
| A13 | Inventario de unidades, capturas y estados | Implementado |
| A14 | Log JSONL de adquisición y eliminación, sin reporte separado | Implementado |
| A15 | Reintentos HTTP/red y detección de listados incompletos de PR | Implementado |
| A16 | Reutilizar capturas de enlaces repetidos dentro de una ejecución | Implementado |
| A17 | Eliminar unidades completas mediante sus IDs | Implementado |
| A18 | Actualizar inventario y conservar otras unidades al borrar | Implementado; archivos no se comparten físicamente entre unidades |
| A19 | API Python y adaptador CLI de descarga/borrado | Implementado |
| A20 | Ejecución y pruebas con Python 3.12 | Verificado con 3.12.13 |
| A21 | Ejemplos, instrucciones y límites explícitos | Implementado |

## Reglas de admisión exactas

El catálogo contiene allowed_urls, excluded_urls, oca_repositories y oca_addons. Se rechazan enlaces no permitidos, excluidos, con credenciales o de hosts desconocidos. Se comparan nombres técnicos como identificadores completos, sin distinguir mayúsculas; se decodifican entidades HTML y escapes URL. Se revisa el contenido original textual y el convertido. En PR, la comprobación se aplica también a metadatos, rutas, commits, comentarios, revisiones y diff. Una coincidencia descarta toda la unidad. No se siguen enlaces documentales ni redirecciones automáticamente.

El catálogo de ejemplo contiene un conjunto inicial de nombres obtenidos durante la auditoría de OpenUpgrade, no un inventario exhaustivo de addons OCA. Su allowed_urls está vacío intencionadamente: no se autoriza material sin revisión. Es necesario completar y mantener el catálogo para el corpus utilizado. No existe un clasificador semántico: puede haber falsos positivos y soluciones copiadas sin nombres detectables. El componente no garantiza ausencia absoluta de filtraciones.

Las fuentes desconocidas se rechazan antes de descargarlas. Para revisar una fuente permitida cuyo contenido cambió, la respuesta necesariamente se lee en memoria; si resulta mixta se descarta sin guardar sus cuerpos. El log y el inventario conservan su ID, URL y motivo, no el contenido excluido.

## Documentos

HTML se convierte a texto con enlaces y saltos estructurales; se excluyen script/style de la representación, pero se inspecciona también el HTML original. Markdown o texto se conservan sin resumir. Solo se admiten conversiones textuales soportadas. PDF, imágenes, ZIP y binarios declarados se excluyen y registran porque este componente no puede inspeccionarlos ni convertirlos con fiabilidad. No se implementó extracción PDF ni OCR.

## PR

Solo merged_at no nulo permite continuar. Se conserva todo el JSON devuelto por los endpoints consultados y el diff. Los listados se paginan y se compara el número de archivos/commits con los contadores del PR. Inconsistencias producen estado incomplete. Estado failed representa errores HTTP/red o de conversión. Comentarios y revisiones reflejan lo disponible durante la captura; no hay snapshot atómico de endpoints y comentarios pueden cambiar mientras se consulta. No se descargan adjuntos externos ni se siguen enlaces.

## Eliminación

Otro componente llama delete_units(session_id, unit_ids, output). Los archivos de cada unidad son independientes: borrar una no borra otra ni requiere calcular referencias compartidas. Se validan IDs, límites de almacenamiento, symlinks y junctions antes de eliminación recursiva. Se conserva inventario/log para registrar el borrado. No hay limpieza automática ni borrado por chunks. Uso previsto: un escritor por sesión; no se implementa coordinación concurrente de inventarios.

## Verificación

21 pruebas locales con respuestas simuladas: conversión, exclusión previa a red, rechazo por contenido/enlaces OCA, entidades HTML, diffs REST, PR completos/fusionados, comentarios mixtos, paginación, captura incompleta, reintento HTTP, errores sin cuerpos sensibles, rutas y eliminación aislada. No se ejecutó una descarga real de producción con este flujo final. La aceptación académica del corpus requiere revisar su catálogo, no solamente pasar estas pruebas.
