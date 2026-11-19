> Alcance aclarado por el usuario: exploración y relaciones pertenecen al componente siguiente. Véase [la reauditoría](REAUDITORIA_ACQUISITION_2026-11-17.md); esas tareas no deben interpretarse como fallos de Acquisition.

# Auditoría exclusiva de Acquisition — 17 de noviembre de 2026

Esta auditoría responde si el primer componente cumple su backlog y el comportamiento descrito por el usuario. Se ejecutó solo adquisición: plan, catálogo, HTTPS, admisión, conversión documental interna, almacenamiento temporal, inventario, log, caché y eliminación. No se ejecutaron ingestion, conversion de diffs, SQLite, grafo, BM25 ni evaluación de migraciones. Los nueve archivos del componente final permanecen idénticos al baseline.

## Dictamen

Hay evidencia real de descarga y almacenamiento de documentación, manifiestos y diffs Odoo, guías y PR de OCA maintainer-tools, y scripts OpenUpgrade. También se comprobaron rechazo por catálogo, caché y borrado aislado. Esto no acredita cumplimiento integral: se reprodujo un error no controlado de conversión, se identificaron falsos positivos del filtro y hay diferencias entre el contrato escrito y la descripción actual del usuario.

El backlog final recibe URLs explícitas y un catálogo. No descubre todos los enlaces de repositorios u organizaciones, no analiza el módulo del partner y no elimina hunks individuales. Una coincidencia literal de exclusión descarta toda la unidad. Por tanto, recolectar automáticamente todo lo pertinente y eliminar únicamente lo relacionado semánticamente con el addon no está implementado en este componente.

## Descargas reales y admisión

La observabilidad utilizó un wrapper que delega en el opener urllib original y devuelve sus bytes sin cambiarlos. No se simuló HTTP en estos casos. El registro solo guarda URL, estado, tamaño y nombres coincidentes del catálogo; no conserva cuerpos excluidos.

| Fuente | Resultado observado |
|---|---|
| odoo-doc-text | accepted |
| odoo-doc-html | excluded: OCA addon identifier detected; entire unit excluded |
| odoo-manifest | accepted |
| odoo-diff | accepted |
| odoo-pr | excluded: PR is not merged |
| oca-tools | accepted |
| openupgrade-doc | excluded: OCA addon identifier detected; entire unit excluded |
| openupgrade-mixed-script | excluded: OCA addon identifier detected; entire unit excluded |
| oca-partner | excluded: OCA addon identifier detected; entire unit excluded |
| openupgrade-crm-script | accepted |
| oca-tools-merged-pr | accepted |

La página ORM respondió HTTP 200 y se descartó por knowledge, presente en el catálogo de identificadores OCA. La prueba controlada de la frase ordinaria “General knowledge about framework maintenance” también se descarta: el componente detecta palabras, no la relación con sale_advance_payment. La documentación OpenUpgrade probada coincidió con knowledge y con una referencia a OCA/account-invoicing; su script mixto de base coincidió con coupon_commercial_partner_applicability, loyalty_partner_applicability y website_sale_require_login. El script CRM adicional fue aceptado.

El catálogo original tiene 252 identificadores y ocho repositorios, pero no sale_advance_payment. Para la ejecución real se añadieron el addon objetivo y OCA/sale-workflow. El ejemplo no se presenta como exhaustivo y no se cambió el código del filtro.

## Funciones y flujo comprobados

1. Validar el plan y construir SourcePolicy con un catálogo obligatorio.
2. Revisar todas las URLs de una unidad antes de pedir su primer archivo.
3. Obtener HTTPS real; GitHub construye endpoints y pagina sus recursos.
4. Inspeccionar texto recibido y texto convertido. Una coincidencia descarta la unidad completa.
5. Escribir archivos de unidades admitidas; registrar capturas, inventario y log.
6. Reutilizar la respuesta en memoria para URLs repetidas, con archivos físicos separados.
7. Borrar unidades por ID mediante API/CLI, actualizar inventario y conservar las restantes.

## Matriz contra el backlog

| ID | Estado de auditoría | Evidencia y límite |
|---|---|---|
| A01 | Parcial | Validación de IDs, files y catálogo en pruebas originales/inspección. before/after sin files se rechaza; claves adicionales before/after junto a files se ignoran, no se rechazan. La lectura estricta de esa prohibición necesita aclaración. |
| A02 | Comprobado en casos ejecutados | Archivos admitidos completos; las unidades mixtas se descartan enteras. No se crean ni recortan hunks. |
| A03 | Comprobado | Sesiones y carpetas por unidad dentro de temp_data; rutas registradas en los inventarios reales. |
| A04 | Comprobado | Manifiesto real de sale de Odoo 17 aceptado: 3180 bytes; no se clonó ni descargó todo el repositorio. |
| A05 | Parcial | RST y Markdown reales aceptados; conversión HTML probada con fixture. La página ORM real se rechazó por knowledge. Un charset desconocido aborta el plan con LookupError. |
| A06 | Comprobado con alcance acotado | Diff real de un commit oficial descargado con HTTP 200: 158315 bytes. La comparación completa 16.0...17.0 previamente produjo HTTP 422; no se afirma cobertura completa. |
| A07 | Comprobado | La URL no revisada se rechazó antes de la red; solo se admitieron enlaces explícitos del catálogo. |
| A08 | Regla literal comprobada; alcance limitado | Rechazo antes de red del addon objetivo al añadirlo al catálogo. No hay inferencia de relación directa; knowledge produce coincidencias sin relación con el partner. El ejemplo original no incluye sale_advance_payment. |
| A09 | Comprobado según backlog | Unidad mixta bloqueada antes de peticiones; script OpenUpgrade mixto descargado en memoria y excluido sin persistir el cuerpo. Se rechaza todo, no solo sus fragmentos OCA. |
| A10 | Comprobado por inspección y ejecución | Política fija y catálogo, sin interruptores ni splits dentro del componente. |
| A11 | Comprobado en PR OCA real | OCA/maintainer-tools#684: merged_at no nulo, descripción y diff, un archivo, un commit, un comentario, una revisión y cero comentarios de revisión. Los PR Odoo consultados con merged_at null se rechazaron, conforme a la regla. |
| A12 | Comprobado | Inventarios con IDs, URLs, fechas, estado y archivos; ningún hash de contenido calculado por Acquisition. Los hashes de integridad de esta auditoría son externos. |
| A13 | Comprobado con límite de error | Inventarios reales accepted/excluded/deleted. Los estados failed/incomplete se prueban con fixtures; la excepción de charset puede interrumpir su escritura. |
| A14 | Parcial | Log JSONL y borrados reales presentes; sin capture-report separado. LookupError puede escapar antes de registrar la unidad fallida. |
| A15 | Comprobado con fallos controlados | HTTP 503 y listados incompletos en la suite original. URLError recuperable, URLError persistente y TimeoutError adicionales: tres intentos y esperas de uno y dos segundos. |
| A16 | Comprobado con red real | Dos unidades con el mismo changelog hicieron una sola petición. Sus archivos están en directorios independientes. |
| A17 | Comprobado con datos reales | delete_units eliminó la unidad duplicada; la CLI propia capturó y borró otra unidad real. |
| A18 | Comprobado | Inventario actualizado a deleted; hashes externos y existencia de todas las otras unidades admitidas se conservaron. |
| A19 | Comprobado | API capture_plan/delete_units y CLI python -m r2.adquisition capture/delete ejecutadas. No se invocaron constructores o consultas R2. |
| A20 | Comprobado | Ejecución actual con Python 3.12.14. Las 21 pruebas originales del componente pasan. |
| A21 | Disponible con observación | Ejemplos y límites presentes. El README interno conserva comandos del paquete standalone; en este proyecto la ruta correcta es python -m r2.adquisition, documentada fuera del componente final. |

“Comprobado” significa observado en los casos indicados o en pruebas controladas explícitas, no una garantía sobre todas las fuentes o errores posibles. Las 21 pruebas originales pasan; las sondas adicionales no se ocultan dentro de ese resultado.

## Hallazgos pendientes

1. **Error de conversión reproducible:** con Content-Type text/plain; charset=nonexistent-r2-audit-encoding, document_text lanza LookupError. capture_plan no lo captura: el plan se aborta y la unidad posterior no se descarga. Se esperaba failed para esa unidad y continuar con la siguiente. Afecta A05/A14 y la robustez del inventario.
2. **Exclusión literal con falsos positivos:** knowledge bloqueó documentación oficial. No es una comprobación de relación directa con el partner. El backlog reconoce falsos positivos, pero el criterio semántico solicitado por el usuario necesita otra definición e implementación.
3. **Configuración del objetivo:** no hay parámetro de módulo objetivo ni análisis del código del partner. Su identificador y repositorio deben incorporarse manualmente al catálogo; su ausencia permite contenido que lo mencione.
4. **Granularidad distinta:** el backlog exige excluir unidades mixtas completas. Recortar hunks y conservar lo demás contradice ese contrato y no existe aquí.
5. **Cobertura de recolección:** el componente descarga un plan cerrado. No descubre automáticamente documentación, PR o archivos de una organización completa. El catálogo permitido del ejemplo está vacío y debe prepararse.
6. **Esquema permisivo:** los campos before/after adicionales se ignoran cuando también hay files. Su prohibición no se valida estrictamente; el formato antiguo sin files sí se rechaza.
7. **Documentación de integración:** el README interno conserva la invocación standalone. Las instrucciones vigentes del proyecto usan r2.adquisition.

## Evidencia y reproducción

- Backlog contractual: [backlog_adquisition.md](../reference/adquisition-final/backlog_adquisition.md).
- [Reporte real](../temp_data/acquisition-only-audit-20261117/live-report.json): los doce casos iniciales, peticiones, comprobaciones de caché/borrado y CLI.
- [Fuentes adicionales](../temp_data/acquisition-only-audit-20261117/extra-live-report.json): script CRM OpenUpgrade y PR fusionado OCA completos.
- [Sondas controladas](../temp_data/acquisition-only-audit-20261117/controlled-probes.json): reintentos, charset, esquema y límites del catálogo.
- [Pruebas originales](../temp_data/acquisition-only-audit-20261117/component-tests.txt): 21 aprobadas, solo el componente final.
- [Inventario principal antes del borrado](../temp_data/acquisition-only-audit-20261117/inventory-before-delete.json).

Los datos completos y runners de esta auditoría permanecen en temp_data, excluidos de Git. Este informe es ligero y no modifica el backlog ni el código final. No se construyó una base de cambios y no se atribuyen hallazgos de migración a esta comprobación.

## URLs consultadas por Acquisition

- https://raw.githubusercontent.com/odoo/documentation/17.0/content/developer/reference/backend/orm/changelog.rst — HTTP 200
- https://www.odoo.com/documentation/17.0/developer/reference/backend/orm.html — HTTP 200
- https://raw.githubusercontent.com/odoo/odoo/17.0/addons/sale/__manifest__.py — HTTP 200
- https://api.github.com/repos/odoo/odoo/compare/6d6e53dc20a506af2bb5dd25e2360c13d024a0eb...cdaa761cedf657614c30c3d8b146054812daf3fe — HTTP 200
- https://api.github.com/repos/odoo/odoo/pulls/95589 — HTTP 200
- https://raw.githubusercontent.com/wiki/OCA/maintainer-tools/Migration-to-version-17.0.md — HTTP 200
- https://oca.github.io/OpenUpgrade/070_migration_files.html — HTTP 200
- https://raw.githubusercontent.com/OCA/OpenUpgrade/16.0/openupgrade_scripts/scripts/base/16.0.1.3/pre-migration.py — HTTP 200
- https://raw.githubusercontent.com/OCA/OpenUpgrade/17.0/openupgrade_scripts/scripts/crm/17.0.1.8/pre-migration.py — HTTP 200
- https://api.github.com/repos/OCA/maintainer-tools/pulls/684 — HTTP 200
- https://api.github.com/repos/OCA/maintainer-tools/pulls/684/files?per_page=100&page=1 — HTTP 200
- https://api.github.com/repos/OCA/maintainer-tools/pulls/684/commits?per_page=100&page=1 — HTTP 200
- https://api.github.com/repos/OCA/maintainer-tools/issues/684/comments?per_page=100&page=1 — HTTP 200
- https://api.github.com/repos/OCA/maintainer-tools/pulls/684/reviews?per_page=100&page=1 — HTTP 200
- https://api.github.com/repos/OCA/maintainer-tools/pulls/684/comments?per_page=100&page=1 — HTTP 200
- https://api.github.com/repos/OCA/maintainer-tools/pulls/684 — HTTP 200
