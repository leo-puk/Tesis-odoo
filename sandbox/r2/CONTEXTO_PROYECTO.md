# Contexto del proyecto R2

Documento global de contexto, implementación, evidencias y pendientes. Debe consultarse junto con REQUISITOS.md. Este archivo puede actualizarse conforme avanza el trabajo. **No altera requisitos: REQUISITOS.md solo se edita por indicación expresa del usuario.** Ambos constituyen las dos fuentes activas de especificación del proyecto; README es únicamente un índice y los documentos de archive/reference/audit son antecedentes o evidencias.

## Estado vigente del flujo consolidado

R2.1 usa una sola ruta operativa. Adquisición recibe el plan y el catálogo. Normalización valida las capturas admitidas y persiste los originales, las unidades, las entidades y el índice BM25 por unidad en SQLite. El cruce extrae coincidencias técnicas del módulo original. La extracción y el recorrido de relaciones usan esas coincidencias para llegar a nuevas unidades. El reporte filtra por salto y capa, deduplica los bloques de diff idénticos y conserva la evidencia, el camino y los conteos antes del límite de presentación.

El constructor activo es `r2.normalization.storage.build_normalized`. Conserva el esquema 4 y distingue el diseño mediante `layout=normalized-units`. Las bases nuevas prescinden de las proyecciones de cambios, elementos y relaciones precalculadas. El código que importaba snapshots y proyectaba diffs se conserva para reproducir pruebas y entregas históricas. La CLI activa usa `run` para todo el flujo, `query` para una base existente y el mismo reporte para comparar con BM25. Los comandos anteriores de construcción del esquema 2 y de consultas sobre proyecciones salen de la CLI.

`r2.extract_relations` contiene el extractor estático compartido. `r2.relations` identifica conexiones entre unidades y recorre su vecindario. La relación activa expresa una identidad técnica compartida. La aplicabilidad de un cambio al módulo todavía requiere comprobar lo descrito por la fuente y sus condiciones. El reporte muestra bloques candidatos y registra el mismo ID de cambio para copias exactas en la comparación de motores. La unidad de cambio semántico queda definida por el protocolo y los juicios de evaluación.

Para R2.2, las pruebas integran captura con transporte simulado, normalización real, SQLite, cruce, relaciones, reporte y comparación léxica. Cubren exclusiones, filtro de versión, deduplicación, conteos antes del límite, trazabilidad y resultados sin juicios. C1, P1 y C2 dependen de referencias y revisiones independientes. V1 tiene una comprobación estructural y T1 separa la preparación de la consulta. La evaluación de tesis requiere el conjunto reservado de MIG, sus juicios y parámetros congelados. Consulta el [README](README.md) para ejecutar el flujo y preparar los insumos.

## Historial de implementación

Las secciones siguientes preservan decisiones, pruebas y pendientes tal como se registraron en cada revisión. Sus comandos y estados corresponden a esas instantáneas.

### Propósito y límites de la entrega anterior

R2 construye y consulta información de migración de Odoo 16–19 de manera determinista. No conecta IA, no ejecuta código de módulos analizados ni acredita por sí solo una migración o equivalencia funcional. La tesis Word permanece intacta. R4, modelo/snapshot/corte y revisores académicos continúan pendientes.

## Responsabilidad de los componentes

- Un componente anterior prepara los enlaces y el plan. Acquisition los recibe; no los descubre ni selecciona por pertinencia.
- Acquisition descarga documentos y archivos completos de fuentes configuradas Odoo, documentación Odoo, OCA maintainer-tools y OpenUpgrade; obtiene diffs oficiales y recursos de PR. Conserva su rechazo de unidades completas según el catálogo fijo.
- La exploración y las relaciones con el addon pertenecen al componente siguiente.
- normalization interpreta originales admitidos, crea unidades con atributos y valida sus localizadores. Su contrato implementado figura en «Normalization: backlog y contrato integrado» de este documento. No genera relaciones de búsqueda.
- collection almacena las unidades en SQLite; query conserva sus consumidores existentes de diffs. La búsqueda nueva entre unidades y su memoria permanecen pendientes.
- crossing realiza el cruce inicial indexado del código del partner con information_units/unit_entities. Es una operación separada de query; no expande relaciones entre unidades ni cambia el baseline BM25.
- evaluation_sources es un cliente separado de metadatos reservados sin soluciones. La evaluación académica requiere responsables, juicios y protocolo propios.

## Cambio autorizado el 17 de noviembre de 2026

La entrega original final se conserva íntegra en reference/adquisition-final/adquisition. El usuario autorizó ahora cambios en la versión activa para robustecer codificaciones, separar originales e interpretación y cubrir fuentes. No se sigue exigiendo igualdad entre el código activo y aquella entrega; se verifica que la referencia histórica permanezca intacta. audit/authorization-20261117.json identifica el motivo y los cambios permitidos.

## Contrato operativo actual de Acquisition 0.4

Entrada: plan JSON con id, kind y files, más catálogo obligatorio. No admite before/after. Los enlaces provienen de otro componente. Los tipos implementados son official_code (archivos individuales Odoo), official_manifest, official_documentation, oca_guidance (wiki y archivos de maintainer-tools), openupgrade_analysis, github_diff y github_pr. No se descargan repositorios completos ni adjuntos externos por inferencia.

Cada entrada del plan es una unidad y puede agrupar varios archivos. Un hunk es un bloque de diff; Acquisition no lo analiza o recorta. Una exclusión descarta el grupo completo, incluidos originales mantenidos temporalmente en memoria. La política conservadora continúa buscando URLs e identificadores del catálogo: esto puede rechazar knowledge dentro de documentación oficial; no se relaja esa regla en esta entrega.

Las unidades admitidas conservan bytes originales, incluidos BOM, CRLF, HTML, scripts y entidades. La extensión refleja el recurso; no se produce una versión TXT a partir de HTML. Un PR se guarda como un bundle JSON con todos los recursos consultados y su diff: es la representación agregada de los valores devueltos, no una copia byte a byte de las siete respuestas HTTP individuales.

La decodificación se usa exclusivamente para admisión: BOM, codificación declarada válida y fallback UTF-8 estricto, sin reemplazar bytes inválidos ni adivinar Latin-1. Si el texto no puede inspeccionarse, la unidad se conserva como quarantined, con sus bytes y metadatos, y el lote continúa. No es accepted y ingestion la excluye. Esta cuarentena es una decisión de ingeniería para cumplir la continuidad sin fingir admisión del contenido; puede revisarse sin reescribir la instrucción literal del usuario.

Estados: accepted, excluded, quarantined, incomplete, failed y deleted. Inventario, capturas y log conservan resultado, URLs y motivos. file_metadata registra encoding de cribado, fallback y text_conversion=not_performed. No se calculan hashes dentro de Acquisition. Las comprobaciones de integridad externas y el almacén posterior sí pueden hacerlo, identificando su alcance.

PDF, imágenes, ZIP y binarios declarados siguen rechazados por no poder inspeccionarse con las reglas de admisión textual actuales. No se presume soporte universal de formatos. Una codificación desconocida ya no debe abortar el plan; si ninguna lectura sin pérdida es posible, se aparta en cuarentena. Errores HTTP/red se registran por unidad; hay reintentos acotados para fallos transitorios y respuestas interrumpidas. Las redirecciones siguen exigiendo URLs explícitas.

## Frontera de conversión actual

Normalización procesa UTF-8 estricto, BOM Unicode y las codificaciones documentadas por Acquisition o Content-Type. Conserva bytes originales y texto decodificado por separado. Una codificación desconocida o ilegible genera una incidencia de normalización; no cambia la admisión ni reemplaza caracteres. La fuente permanece disponible y se continúa con las demás. Los límites del parser y los campos desconocidos se registran explícitamente.

## Ejecución local

Desde la raíz del proyecto:

```powershell
.\r2.ps1 capture-plan PLAN.json --catalog CATALOGO.json --output temp_data
.\r2.ps1 delete-units SESION UNIDAD --output temp_data
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

La CLI propia también está disponible mediante python -m r2.adquisition capture/delete. build produce esquema 4; --bindings aporta versiones y metadatos explícitos, pero es opcional. build-legacy identifica reconstrucción local histórica. Las bases existentes no se sobrescriben y los esquemas 2/3 continúan siendo legibles. Las demos siguen siendo casos de desarrollo, no resultados académicos.

## Datos, Git y procedencia

Repositorio: https://github.com/leo-puk/Tesis-odoo, rama master. temp_data y data_temp están ignorados en toda la repo. No se publican automáticamente datos de nuevas pruebas ni cambios de código. El componente original y sus tests se conservan en reference; archive contiene versiones anteriores.

## Estado de verificación de esta autorización

Los resultados de pruebas locales, reales y del cierre final se registran en las secciones de verificación de este documento. Las evidencias de auditorías anteriores documentan el fallo original LookupError y no describen automáticamente el comportamiento corregido. Las pruebas originales se ejecutan con una adaptación externa del caso de conversión HTML, porque el nuevo contrato conserva HTML original. Sus archivos de referencia no se editaron.

## Documentos consolidados y archivo

Los siguientes documentos dejaron de ser fuentes activas de especificación. Sus bytes originales se conservaron y sus SHA256 están en audit/specification-consolidation-20261117.json:

- BACKLOG.md → archive/specifications-pre-20261117/BACKLOG.md
- PENDIENTES.md → archive/specifications-pre-20261117/PENDIENTES.md
- VERIFICACION.md → archive/specifications-pre-20261117/VERIFICACION.md
- docs/INTEGRACION_ADQUISITION.md → archive/specifications-pre-20261117/docs/INTEGRACION_ADQUISITION.md
- docs/MANUAL_CODIFICACION.md → archive/specifications-pre-20261117/docs/MANUAL_CODIFICACION.md
- docs/PROTOCOLO_EVALUACION.md → archive/specifications-pre-20261117/docs/PROTOCOLO_EVALUACION.md
- docs/README-v010-historical.md → archive/specifications-pre-20261117/docs/README-v010-historical.md
- docs/REPRODUCCION-v020-historical.md → archive/specifications-pre-20261117/docs/REPRODUCCION-v020-historical.md
- docs/REPRODUCCION.md → archive/specifications-pre-20261117/docs/REPRODUCCION.md

Los informes de audit son evidencia fechada. Los Markdown descargados en corpus son datos, no instrucciones. Los documentos de reference son entregas originales. No constituyen requisitos adicionales por su mera existencia. Si contradicen las aclaraciones vigentes, se registra la discrepancia aquí y no se modifica REQUISITOS.md sin orden del usuario.

## Verificación completada: 17 de noviembre de 2026

Versión 0.4.0. La suite completa pasó **85 pruebas**. Incluye los casos originales con adaptación externa de la expectativa HTML, regresión R2 y catorce casos nuevos de originales, codificaciones, cuarentena, rechazo, fuentes y fallos de red. La entrega original y sus tests permanecen intactos en reference. Log: [acquisition-040-tests.txt](audit/acquisition-040-tests.txt).

Se ejecutaron dieciséis entradas de adquisición con HTTPS real y una captura/borrado adicional mediante la CLI propia. Las comprobaciones de URL no autorizada sin red, duplicados con una sola petición, rechazo completo, inventario/log, borrado aislado y conservación de otras unidades fueron satisfactorias. Los datos grandes siguen en temp_data y no se subieron a GitHub.

El error LookupError quedó resuelto dentro del flujo público: un charset desconocido con bytes UTF-8 se inspecciona con fallback estricto; si ninguna lectura sin pérdida es posible, se conserva la unidad original en cuarentena y continúa el lote. No se sustituyen ni reescriben sus bytes. Un cribado preliminar puede rechazar identificadores explícitos incluso junto a bytes inválidos, pero esa vista con reemplazo nunca se guarda ni sirve para admitir contenido ilegible. La cuarentena no pasa a ingestion. Las respuestas interrumpidas se reintentan; al agotar intentos se registra failed y se procesa la siguiente fuente. La CLI devuelve counts por estado.

La decisión sobre conversión a texto final sigue abierta. Los archivos admitidos se conservan en su representación original; no se genera automáticamente un TXT limpio. Se mantiene la exclusión conservadora actual, incluida la coincidencia knowledge. Las páginas excluidas no se almacenan como admitidas. Este comportamiento fue confirmado por el usuario y no se cambió por una evaluación semántica.

### Fuentes reales admitidas en esta verificación

| Recurso | URL |
|---|---|
| odoo-doc-text | https://raw.githubusercontent.com/odoo/documentation/17.0/content/developer/reference/backend/orm/changelog.rst |
| odoo-manifest | https://raw.githubusercontent.com/odoo/odoo/17.0/addons/sale/__manifest__.py |
| odoo-diff | https://github.com/odoo/odoo/compare/6d6e53dc20a506af2bb5dd25e2360c13d024a0eb...cdaa761cedf657614c30c3d8b146054812daf3fe |
| oca-tools | https://raw.githubusercontent.com/wiki/OCA/maintainer-tools/Migration-to-version-17.0.md |
| openupgrade-crm-script | https://raw.githubusercontent.com/OCA/OpenUpgrade/17.0/openupgrade_scripts/scripts/crm/17.0.1.8/pre-migration.py |
| oca-tools-merged-pr | https://github.com/OCA/maintainer-tools/pull/684 |
| odoo-source-file | https://raw.githubusercontent.com/odoo/odoo/17.0/odoo/fields.py |
| oca-tool-file | https://raw.githubusercontent.com/OCA/maintainer-tools/master/tools/ocb-sync.sh |

Se conservó también un duplicado del changelog para comprobar caché y eliminación, y se rechazaron las unidades de control esperadas. Un script OpenUpgrade mixto, su documentación con coincidencias excluidas, la página ORM con knowledge y un PR sin merged_at se rechazaron conforme al catálogo/regla vigente. No se declara que todas las URLs posibles o todos los formatos estén soportados.

### Integridad y documentación

[acquisition-040-state.json](audit/acquisition-040-state.json) identifica código, pruebas, wheel y alcance de autorización. Se construyó un wheel 0.4.0 sin descargar dependencias y se probó su importación aislada, incluida la recuperación de charset desconocido. La referencia final original, los documentos archivados y el Word conservan sus bytes. REQUISITOS.md conserva el mismo hash desde su creación autorizada; este resultado solo actualiza contexto.

## Verificación final del backlog de Acquisition — 17 de noviembre de 2026

Se revisaron los 21 puntos A01–A21 contra los requisitos vigentes y sus aclaraciones. Dieciocho mantienen su alcance y están comprobados; A04, A05 y A13 tienen ajustes autorizados y también se comprobaron. No se detectaron defectos bloqueantes en los casos ejecutados. Esto no equivale a garantizar todos los tamaños, formatos o comportamientos de servicios externos.

Se volvieron a ejecutar **35 pruebas focalizadas de Acquisition: todas aprobadas**. Las 85 pruebas citadas antes son del proyecto completo y no se atribuyen todas a este componente. Se verificó que el código productivo no cambió desde aquella suite. Se añadieron **ocho sondas externas de guardas**, todas aprobadas: duplicados, tipo desconocido, contador de commits inconsistente, continuidad tras HTTP 403 y cuatro controles de borrado/rutas, incluidos dos con junctions reales de Windows.

Las junctions solo pudieron crearse fuera de la restricción del entorno, siempre dentro del directorio temporal propio. Acquisition rechazó el destino enlazado y bloqueó el borrado recursivo que contenía otro enlace; se conservaron el archivo de la unidad y el marcador protegido. No se cambió código para pasar estas comprobaciones.

Se revalidaron los inventarios y archivos conservados de las dieciséis entradas reales y la captura/borrado CLI anteriores. No se repitieron descargas innecesarias: el código coincide por hashes con el ya comprobado. Paginación de varias páginas y errores transitorios se verificaron mediante respuestas controladas; el PR real usado es pequeño. No se presenta esa evidencia como una prueba real de todas las páginas posibles.

| ID | Punto del backlog | Resultado | Verificación |
|---|---|---|---|
| A01 | Validar plan, IDs y catálogo | Comprobado | Esquema, catálogo obligatorio, rutas y before/after en pruebas; IDs duplicados y tipo desconocido rechazados sin red en sondas adicionales. |
| A02 | Conservar unidades completas | Comprobado | Originales byte a byte, incluidos HTML/BOM/CRLF, sin resumen o hunks. PR guarda valores completos del bundle, no siete respuestas crudas independientes. |
| A03 | Almacenar en temp_data por sesión/unidad | Comprobado | Carpetas e inventarios reales; una junction real de Windows como destino se rechazó antes de la red. |
| A04 | Descargar manifiestos explícitos | Ajustado y comprobado | Conserva manifiestos y ahora archivos individuales oficiales Odoo por autorización de cubrir archivos. No clona repositorios completos ni ejecuta código. |
| A05 | Documentación y representación textual | Ajustado y comprobado | Descarga y conserva originales. La conversión HTML→TXT/MD se pospuso por instrucción del usuario. Decodificación solo de admisión; fallback estricto o cuarentena sin abortar. |
| A06 | Obtener diffs Odoo mediante REST | Comprobado | Comparación concreta oficial descargada con HTTP 200. El intento amplio 16.0...17.0 tuvo HTTP 422: no se presenta como corpus completo. |
| A07 | Admisión de URLs exactas | Comprobado | URL sin revisar y exclusión explícita se rechazan antes de peticiones. El catálogo lo prepara el componente anterior. |
| A08 | Excluir repositorios e identificadores catalogados | Comprobado | Mantiene rechazo literal, entidades/escapes y nombres completos. Incluye bytes visibles con codificación dañada y BOM Unicode; no promete detección semántica universal. |
| A09 | Excluir unidades mixtas completas | Comprobado | Se descarta todo el grupo y no se escriben cuerpos excluidos; no recorta fragmentos. |
| A10 | Política fija | Comprobado | API/CLI sin interruptor de admisión OCA ni split académico dentro del componente; confirmado por inspección y llamadas. |
| A11 | Recursos de PR fusionados | Comprobado | Guarda pull, files, commits, comments, reviews, review_comments y diff. PR real OCA completo; paginación y contadores incompletos con respuestas controladas, archivos y commits. |
| A12 | ID, URL, fecha, estado y ubicación | Comprobado | Metadatos e IDs presentes. Acquisition no calcula hashes de contenido; los hashes de auditoría son externos. Los SHA upstream que devuelve GitHub son datos de origen. |
| A13 | Inventario de unidades y estados | Ajustado y comprobado | Añade quarantined y file_metadata para preservar originales no inspeccionables. Quarantined no equivale a accepted y no se incorpora al consumidor. |
| A14 | Log JSONL de adquisición y borrado | Comprobado | Eventos finales, motivos, finished, cuarentena y borrados; sin capture-report separado del componente. |
| A15 | Reintentos y detección de incompletos | Comprobado | 503/red/lectura interrumpida probados con fallos controlados; al agotar intentos registra failed y continúa. 403 permanente también continúa. |
| A16 | Reutilizar URLs repetidas | Comprobado | Una petición real para dos unidades con el mismo changelog; archivos separados. |
| A17 | Borrar por IDs de unidad | Comprobado | API y CLI borraron unidades reales. IDs desconocidos o sesión inválida no borran datos; junction interna real impidió recursión. |
| A18 | Actualizar inventario sin afectar otras unidades | Comprobado | Estado deleted y listas vacías; otros archivos reales conservaron existencia y hashes externos. Un borrado bloqueado no modifica los datos protegidos. |
| A19 | API y CLI | Comprobado | capture_plan/delete_units y python -m r2.adquisition capture/delete ejecutados. |
| A20 | Python 3.12 | Comprobado | 35 pruebas focalizadas recién ejecutadas en Python 3.12.14. Código idéntico al de las 85 pruebas generales previas. |
| A21 | Ejemplos, instrucciones y límites | Comprobado | Dos fuentes activas: REQUISITOS.md y CONTEXTO_PROYECTO.md; README como índice, ejemplos y límites explícitos. El historial está archivado. |

### Pendientes y límites de este cierre

- **Conversión definitiva a texto:** pendiente por decisión del usuario. No se considera realizada ni función faltante de Acquisition bajo el alcance actualizado. Se preserva el original.
- **Enlaces/catálogo y exploración:** pertenecen a otros componentes. El catálogo debe suministrarse y mantenerse; no se infiere pertinencia o relación con el addon.
- **Formatos no soportados:** PDF, imágenes, ZIP y binarios declarados siguen excluidos. No se introduce OCR ni clonación completa.
- **Servicios externos:** una respuesta real fallida sigue siendo posible. Se registra sin prometer acceso universal. Los recursos de PR pueden cambiar entre peticiones; no hay snapshot atómico ni escritores concurrentes por sesión.

Fuentes de esta verificación: [matriz estructurada y guardas](audit/acquisition-final-backlog-verification.json), [35 pruebas focalizadas](audit/acquisition-final-backlog-tests.txt), [85 pruebas generales previas](audit/acquisition-040-tests.txt) y las evidencias reales enlazadas arriba. REQUISITOS.md conserva su hash; el resultado solo actualiza contexto y evidencia.

## Cruce inicial: contrato y backlog C01–C15

Alcance autorizado: backlog C01–C15 del usuario, confirmación «ahora si codea» y corrección explícita del adjunto fb659a66-5eb4-4247-8676-0dd956bd2201. El componente se implementa en r2/crossing, con entrada pública cross_module(database, module, module_name=None, output=None) mediante argumentos nombrados para module_name/output. La CLI es cross. Acquisition y query permanecen intactos. El único ajuste compartido de Normalization autorizado en esta revisión es la extracción CSV explícita y su versión de reglas. No se construyen ramas, ranking nuevo, memoria o comparaciones nuevas con BM25.

### Contrato de entrada y salida

Entrada obligatoria: archivo individual o carpeta de código del partner y colección SQLite de esquema 4 con information_units, unit_entities, sources, el índice unit_entity_lookup y reglas normalization-3. Se rechazan colecciones históricas, sin índice o con reglas anteriores: no se cae silenciosamente en changes. module_name es el nombre técnico explícito del addon, opcional; no se deduce del nombre visible del manifiesto ni de un archivo o carpeta. La colección se abre en modo de solo lectura.

El lector admite Python, XML, CSV y manifiestos __manifest__.py. Reutiliza extract_entities y manifest_entities corregidos sin importar ni ejecutar código descargado. Python respeta la codificación declarada por su archivo; XML respeta BOM/declaración. CSV reconoce exclusivamente id y columnas :id mediante un extractor puro compartido, conservando fila, columna y valor original. Se ignoran entornos, cachés y .git; no se siguen archivos o carpetas enlazadas mediante symlinks/junctions. Un archivo individual no provoca lectura de vecinos; una entrada inexistente se distingue de un formato no soportado. Los errores por archivo se registran y los demás se procesan.

Salida JSON, versión 2: component=crossing, rules_version=crossing-2, result_id, colección/revisión/reglas de normalización, input (archivos, entidades, errores y limitaciones), matched_unit_ids, results, unresolved, rejected_candidates, status, outcome, summary y limits. matched_unit_ids es una lista ordenada y sin duplicados. Cada resultado contiene exclusivamente information_unit_id y evidences, nunca una copia de la unidad o su documento. Cada evidencia conserva input_entity y unit_entity como observaciones puntuales, identidad técnica comprobada y match_rule; ambos lados mantienen archivo/localizador, ubicación, tipo, ámbito, origen y regla de extracción. validate_result comprueba la coherencia de IDs, resultados, contadores e identidad antes de devolver o persistir.

status distingue complete/partial; outcome distingue matches, no_matches, no_resolvable_identifiers y undetermined cuando no hay resultados y hubo errores de lectura/análisis. Una ausencia con errores no se presenta como comprobación de ausencia. Las referencias no resueltas permanecen visibles aunque existan otras coincidencias.

Los resultados se ordenan por ID, sin puntuación de relevancia ni límite de diez: esta operación entrega el conjunto inicial de coincidencias, no la primera vista evaluada de R2. Cada unidad aparece una vez y reúne evidencias distintas. Se puede escribir un JSON nuevo mediante output/save_result, sin sobrescribir archivos existentes ni cambiar la colección; no es una memoria de relaciones. No se incluyen tiempos ni fechas variables en el resultado reproducible.

### Reglas de identidad y ámbitos

- En el partner solo origin=code puede ser semilla. En las unidades, origin=code/documentation/comment es elegible si el tipo y ámbito técnico están explícitamente establecidos. Una identifier_mention genérica no se convierte en modelo, campo o método por compartir palabras ni por lookup_keys; sigue sin cruzar. La coincidencia de un comentario tipado no valida su afirmación. La elegibilidad documental tipada se verifica aisladamente porque el normalizador actual no genera esos tipos para muchas menciones documentales.
- Los nombres conservan su escritura exacta, incluidos puntos, mayúsculas y guiones bajos. SQL busca primero por nombre/tipo usando unit_entity_lookup y recupera exclusivamente las unidades candidatas por su clave primaria.
- Métodos y referencias de método constituyen una familia compatible; campos y referencias de campo constituyen otra. Exigen el mismo nombre y un modelo propietario explícito idéntico. Las rutas de campo related también requieren modelo conocido.
- Las funciones locales no se tratan como miembros del modelo ni como funciones globales. Funciones de módulo y clases Python requieren namespace de addon explícito, archivo técnico conocido, ámbito y qualified_name compatibles. Para diffs se usa code_path; un path addons/<addon>/... solo pierde ese prefijo cuando el addon está explícitamente identificado. No se inventa una ruta técnica a partir del nombre local de un archivo capturado.
- Los identificadores externos sin namespace requieren módulo explícito. Se permiten únicamente las variantes exactas local/modulo.local de ese namespace, comprobándolo después de la consulta indexada. Las rutas relativas y claves de manifiesto también requieren addon conocido.
- Modelos, módulos importados/dependencias, opciones de campo y atributos XML reconocidos tienen identidades globales por tipo y nombre. Su coincidencia solo prueba la observación de ese identificador, no una dependencia, relevancia o incompatibilidad.
- self.attribute del código de entrada solo puede refinarse como campo/método si existe una declaración única compatible en el mismo modelo. Si es ambiguo o no está declarado, conserva su estado no resuelto.
- Se comprueba que cada fila del índice corresponda a la entidad y ordinal de su unidad normalizada. Un índice inconsistente provoca un error que pide reconstruir la colección; no produce coincidencias silenciosas.

### Backlog y verificación

| ID | Funcionalidad acordada | Implementación y criterio comprobable |
|---|---|---|
| C01 | Recibir código y colección normalizada | Cumple: archivo/carpeta, API/CLI, salida v2 por IDs y errores explícitos. Pruebas de archivo, esquema e índices. |
| C02 | Leer código sin ejecutarlo | Lector estático, AST/tokens/literales; prueba con import inexistente y raise al nivel superior sin ejecución. |
| C03 | Extraer identificadores explícitos | Cumple: entidades con tipo, ámbito, archivo, ubicación y regla; CSV añade fila/columna/valor mediante convenciones explícitas. |
| C04 | Comprobar ámbitos | Rechaza helper local, propietarios desconocidos, modelos diferentes y namespaces de función incompatibles. |
| C05 | Consultar unidades normalizadas | JOIN de unit_entities e information_units; no consulta changes ni el índice BM25 antiguo. |
| C06 | Cruzar identificadores exactos | Cumple: identidad exacta y políticas separadas por lado. Elegibilidad documental tipada probada aisladamente; la integración conserva el límite de menciones genéricas. |
| C07 | Aprovechar índices | Búsqueda name/type forzada por unit_entity_lookup; prueba EXPLAIN QUERY PLAN y traza SQL sin barrido de textos. |
| C08 | Registrar evidencias | Cada coincidencia contiene observaciones y ubicaciones de ambos lados, regla e identidad. |
| C09 | Deduplicar unidades | Cumple: IDs únicos ordenados, una entrada por unidad y todas sus evidencias distintas, sin copiar contenidos. |
| C10 | Guardar y entregar resultados | Cumple: mismo JSON de API/persistencia, esquema v2 validado, revisión de colección y creación exclusiva. |
| C11 | Informar limitaciones | errors, limitations, unresolved, rejected_candidates, status y outcome diferenciados. |
| C12 | Asegurar resultados reproducibles | Mismas entradas/reglas generan el mismo objeto e ID; no se mezclan tiempos de ejecución. |
| C13 | Integrar con el proyecto | Cumple: API/CLI y SQLite existentes; extractor CSV compartido puro con cambio mínimo autorizado de Normalization. Acquisition/query intactos. |
| C14 | Probar coincidencias y rechazos | Cumple en los casos ejecutados: 35 pruebas de cruce (22 previas y 13 nuevas), más regresión general. El guard de enlace individual se simula por portabilidad. |
| C15 | Documentar contrato y reglas | Cumple: r2/crossing/README.md solicitado, este cruce de evidencia y ejemplos positivos/negativos; no se sustituye un requisito por una limitación. |

### Archivos y uso

code.py lee el módulo y reúne observaciones/errores; rules.py define identidades y familias compatibles; engine.py consulta índices, verifica candidatos, reúne evidencias y guarda el resultado; __init__.py expone cross_module y save_result. Se reutilizan los extractores de normalization y connect/meta de collection. No se introducen dependencias nuevas.

```powershell
.\r2.ps1 cross RUTA_MODULO --db COLECCION.sqlite --module-name nombre_tecnico --output cruce.json
.\.venv\Scripts\python.exe -B -m examples.run_crossing_demo --output temp_data/otro-ejemplo-cruce
```

Demo ejecutada en temp_data/crossing-demo-20261118: once unidades normalizadas a partir de HTTP simulado, tres unidades coincidentes para el módulo positivo y cero para el control. matches.json y no-matches.json contienen los resultados completos; report.json registra el alcance. examples/crossing-results.json conserva la muestra para revisión. No es una migración, descarga real ni evaluación de pertinencia académica.

Suite inicial: 151 pruebas, conservada en audit/crossing-all-tests.txt. Revisión correctiva del adjunto: 35 pruebas de cruce y 164 pruebas generales aprobadas; logs audit/crossing-corrections-focused.txt y audit/crossing-corrections-all-tests.txt. Se cubren IDs sin documento, políticas por lado, archivos individuales, CSV en ambos lados, errores, CLI y persistencia. audit/crossing-corrections.json registra archivos protegidos, excepción mínima CSV y resultados. Estas pruebas no garantizan cobertura semántica completa.

La revisión corrigió cuatro incumplimientos del contrato: copias completas de unidades, elegibilidad documental excesivamente restrictiva, falta de archivo individual y soporte CSV incompleto. No se consideran requisitos aprobados por haber documentado el comportamiento anterior. La guía específica solicitada está ahora en r2/crossing/README.md; se añade por petición expresa, conservando REQUISITOS.md sin cambios.

El extractor CSV histórico ya reconocía id/:id pero generaba relaciones de seguridad; no se reutiliza esa parte. r2/csv_entities.py aplica solo las convenciones explícitas y se llama desde normalization/entities.py. normalization/schema.py versiona el cambio como normalization-3, sin cambiar el esquema de unidad/SQLite. No se infieren modelos desde XML-ID, no se ejecutan celdas ni se crean aristas. Las capturas se conservan: para indexar entidades CSV se reconstruye una colección nueva. El resto del normalizador conserva sus bytes y se verificó mediante regresiones.

La demo actualizada está en temp_data/crossing-corrections-demo-20261118: tres IDs coincidentes y cero para el control negativo, HTTP simulado. examples/crossing-results.json contiene la salida v2 sin unidades completas. Los JSON de la demo inicial conservados en el directorio anterior son antecedentes de esquema v1, no el contrato actual.

Quedan fuera de C01–C15: localizar referencias dinámicas no demostrables, evaluar aplicabilidad/incompatibilidad, descubrir relaciones entre unidades, recorrer ramas, guardar memoria y adaptar BM25. La comparación futura debe utilizar la misma colección de unidades y filtros; este cruce inicial no se presenta como una comparación nueva contra el baseline histórico.

## Normalization: backlog y contrato integrado

Autorización: adjunto 2d023f2b-3d8f-462d-874a-db1441efe000, «Quiero que ajustes e integres el componente normalization». Este apartado es el Markdown de backlog/contrato solicitado, integrado aquí para conservar las dos fuentes globales acordadas. Distingue el contrato solicitado, las decisiones técnicas de implementación y sus límites. No se atribuye TF-IDF ni este esquema concreto al texto de la tesis, ni se modifica REQUISITOS.md o el Word.

### Contrato acordado

Entrada: inventario de Acquisition y sus archivos originales. Solo se procesan entradas accepted. Los estados restantes se informan como no procesados, respetando la admisión anterior. No se vuelve a aplicar el catálogo. Los metadatos de procesamiento pueden suministrarse en bindings.sources; los valores ausentes permanecen desconocidos.

Salida de normalize_session(inventory, bindings=None): sources, artifacts, units, issues, warnings, normalization y excluded. Una fuente representa cada archivo completo recibido, conservando la identidad de la captura y de la unidad de adquisición. Una unidad normalizada deriva de una ubicación verificable en esa fuente. No se borran ni sobrescriben originales. No se generan relaciones entre unidades, grafos ni memoria de consultas.

### Backlog de implementación

| ID | Trabajo y criterio | Estado y evidencia |
|---|---|---|
| N01 | Leer inventario y procesar exclusivamente accepted, validando rutas locales | Implementado; tests de estados, rutas y aislamiento previos más integración nueva. |
| N02 | Respetar codificaciones documentadas y conservar originales sin reemplazos | Implementado; Latin-1, BOM UTF-16, charset desconocido, original Base64 y continuidad. |
| N03 | Crear una unidad por bloque @@, manteniendo archivo y rangos | Implementado; creados/eliminados, /dev/null, varios archivos/bloques y localizadores. |
| N04 | Segmentar Markdown por encabezados verificables y preservar contenido | Implementado; ATX/Setext fuera de cercas; prefacio conservado y código cercado sin encabezados falsos. |
| N05 | Conservar TXT sin límites estructurales fiables | Implementado; un documento completo, incluidos párrafos y saltos. |
| N06 | Interpretar un manifiesto literal completo sin ejecutarlo | Implementado; ast.literal_eval, claves/listas verificadas y prueba de contenido ejecutable rechazado. |
| N07 | Separar descripción, diff, comentarios, revisiones y commits del PR | Implementado; JSON pointers, contexto común, recursos sin cuerpo y procedencia de patches. |
| N08 | Evitar evidencia duplicada por diff/patch dentro del mismo PR | Implementado; /diff canónico, referencias a files[].patch y un único registro por hunk canónico. |
| N09 | Extraer entidades exactas con tipo, ubicación, regla y contexto | Implementado; Python AST/tokens, XML, manifiesto y menciones delimitadas en documentos/comentarios. |
| N10 | Separar términos léxicos, frecuencias y pesos TF-IDF | Implementado; stop words explícitas, sin stemming y corpus/configuración registrados. |
| N11 | Validar esquema, identidad y correspondencia con el artefacto retenido | Implementado; campos obligatorios, tipos, IDs, rangos y rutas JSON comprobados. |
| N12 | Integrar almacenamiento y lectura sin sustituir SQLite | Implementado; esquema 4, information_units, índices de entidades/términos y exportación. |
| N13 | Mantener reproducibilidad e idempotencia de la misma captura | Implementado; orden estable, repetición idéntica, deduplicación por ID y reconstrucción idéntica de colección. |
| N14 | Retirar las relaciones del flujo de normalización | Implementado; convert_units no devuelve aristas y la tabla relations de las nuevas colecciones está vacía. |
| N15 | Proteger consumidores existentes y colecciones anteriores | Implementado; proyección de diffs, consulta/BM25/exportación y esquemas 2/3 cubiertos por regresión. |
| N16 | Entregar ejemplos inspeccionables por formato y pruebas ejecutadas | Implementado; demo reproducible con HTTP simulado y unidades JSON. Suite inicial de 109 y regresión posterior de 129 pruebas; véanse las correcciones siguientes. |

### Esquema explícito de unidad, versión 1

| Atributo obligatorio | Significado y condición |
|---|---|
| id | Identidad reproducible de captura, localizador, regla y versiones de esquema/reglas. No identifica equivalencia entre capturas diferentes. |
| source_id | Fuente completa de la que procede; distingue archivos dentro de una misma entrada de adquisición. |
| source_url | URL registrada del archivo o null si no puede atribuirse sin suponer. |
| source_locator | artifact_path y, según formato, line_start/line_end o json_pointer. Las líneas de /diff son del string JSON decodificado, no del documento JSON serializado. HTML solo declara el artefacto, sin inventar líneas del texto extraído. |
| kind | diff_hunk, markdown_section, text, manifest, pr_description, pr_comment, pr_review, pr_review_comment, pr_commit, code, html_document o rst_section. |
| text | Contenido de la unidad, conservando encabezados/bloques según corresponda. |
| version_from / version_to | Versiones explícitas o null; no se infieren del nombre de rama, URL ni versión del manifiesto. |
| layers | Clasificación verificable del archivo/formato: python, xml, data, manifest, documentation o unknown; no certifica la capa afectada por una incompatibilidad. |
| entities | Observaciones con name exacto, type, location, rule y context. origin distingue code, documentation y comment. lookup_keys conserva identificadores de consulta existentes, sin resolver relaciones. |
| terms | Lista ordenada de term, frequency y tfidf; las frecuencias se conservan. |
| extraction_rule | Regla de segmentación aplicada. |
| schema_version | 1 para este contrato de unidades; independiente del esquema 4 de SQLite. |
| warnings | Limitaciones, campos desconocidos y advertencias específicas de esa unidad. |

Metadatos adicionales: artifact_id, rules_version, encoding, normalization_status (valid o partial), terms_corpus_id y data con información propia del formato. Los fallos que impiden crear una unidad se registran en issues con fuente, artefacto, ubicación, fase y detalle. Una unidad estructuralmente válida no certifica incompatibilidad, solución ni aplicabilidad.

El diff conserva old_path/new_path, file_path, rangos antes/después, contexto, removed/added y cabecera/cuerpo del hunk. No reconstruye archivos completos. Los fragmentos incompletos solo reciben atributos respaldados por reglas locales; no se inventa su modelo propietario.

### Métodos, herramientas y decisiones técnicas

| Herramienta o método | Uso concreto | Alcance y procedencia |
|---|---|---|
| Python 3.12, pathlib y json | Leer capturas, crear registros y resolver localizadores | Lenguaje ya seleccionado en el proyecto; organización interna de ingeniería. |
| ast y ast.literal_eval | Reconocer declaraciones/literales y leer manifiestos | Sin ejecutar código. Su aplicación aquí es una decisión técnica; no se presenta como obligación nueva de la tesis. |
| tokenize y re | Patrones conservadores en fragmentos incompletos y menciones explícitas | Reglas reproducibles; sin inferencia de llamadas, afectación o relaciones entre unidades. |
| lxml | Texto HTML y observaciones XML con red/DTD desactivados | Conserva el original; no valida el funcionamiento de Odoo. |
| scikit-learn TfidfTransformer | Pesos léxicos sobre frecuencias | TF-IDF es una decisión pedida por este adjunto; no reemplaza BM25 ni decide vínculos. |
| SQLite existente | Unidades, originales, incidencias y atributos indexados | No hay otra base de datos. Las tablas antiguas sirven de proyección de compatibilidad. |
| unittest | Contratos, errores, integración y regresión | Pruebas de ingeniería con datos sintéticos; no evaluación académica. |

Tokenización léxica: patrón Unicode [^\\W\\d]\\w*, minúsculas, sin stemming, con stop words inglesas/españolas explícitas en normalization/terms.py y en los metadatos. Los identificadores técnicos mantienen mayúsculas/minúsculas, puntos y guiones bajos originales. TF-IDF usa norm=l2, use_idf=True, smooth_idf=True, sublinear_tf=False. Se registran versión de scikit-learn, lista de unidades, vocabulario, IDF, configuración y corpus_id basado en textos/configuración. Cambiar el corpus puede cambiar los pesos sin cambiar la identidad de una unidad. Referencia de implementación: [TfidfTransformer 1.7.2](https://scikit-learn.org/1.7/modules/generated/sklearn.feature_extraction.text.TfidfTransformer.html).

### Organización y entrega a almacenamiento

readers.py valida/carga la captura; decoding.py resuelve la lectura sin pérdida; parsers.py aplica límites de formato; diff.py conserva el parser de diffs; entities.py reconoce observaciones; observations.py coordina esas reglas con el formato y sistema de coordenadas de cada parte, compartido por conversor y validador; anchors.py aporta patrones parciales; terms.py calcula frecuencias/pesos; schema.py valida; units.py construye unidades; pipeline.py coordina. Los puentes anteriores de ingestion/conversion conservan importaciones existentes sin duplicar implementación. text.py conserva únicamente el conversor histórico utilizado por reconstrucciones antiguas.

collection.build_session consume la salida validada, genera vistas de compatibilidad y llama al escritor SQLite. information_units es la representación principal; unit_terms y unit_entities contienen índices por atributo. artifacts conserva texto y bytes originales en Base64, además de metadatos ya existentes. El inventario y los archivos de Acquisition no se editan. La tabla relations queda vacía en esquema 4.

Los consumidores antiguos reciben una proyección de los hunks como candidatos textuales, nunca incompatibilidades verificadas automáticamente. Un intervalo desconocido conserva la unidad completa, pero no se inventa un intervalo para esa proyección de consulta de migración. query conserva los motores y ranking anteriores; sus citas contextuales explícitas se resuelven al consultar. Las nuevas unidades documentales son inspeccionables con export; la recuperación documental y las relaciones ramificadas nuevas quedan para el componente de búsqueda.

No se exige SHA inmutable ni un hash externo para aceptar la entrada. Se preservan los hashes que el lector ya calculaba y se usan fingerprints internos para identidad/reproducibilidad. Las colecciones existentes no se sobrescriben: un reprocesamiento puede generar otra base y la misma revisión de colección para las mismas entradas y configuración.

### Ejemplos y comprobación ejecutada

Demo: examples/run_normalization_demo.py. Cinco capturas aceptadas mediante transporte HTTP simulado produjeron once unidades, nueve tipos, cero incidencias y cero relaciones de búsqueda. Incluye Markdown, TXT, manifiesto, diff y recursos separados de PR. No es una descarga real ni una migración de Odoo.

Resultados inspeccionables: temp_data/normalization-demo-20261118/units.json, normalization.json, report.json y collection.sqlite. El directorio temporal continúa ignorado por Git. Las muestras compactas conservadas para revisión están en examples/normalization-units.json; registran IDs y localizadores reales de esta demo sintética, sin suplantar una fuente descargada de internet.

Comandos:

```powershell
.\.venv\Scripts\python.exe -B -m examples.run_normalization_demo --output temp_data/otra-demo-normalization
.\.venv\Scripts\python.exe -B -m r2 build INVENTORY.json --bindings BINDINGS.json --db collection.sqlite
.\.venv\Scripts\python.exe -B -m r2 export --db collection.sqlite
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Suite completa: 109 pruebas aprobadas, con veinte casos nuevos específicos de normalización y ajustes de expectativas que codificaban el contrato anterior. Log: audit/normalization-integration-tests.txt. Incluye el caso funcional OCA con HTTP/revisión simulados, compatibilidad con colecciones históricas y preservación de identificadores XML tras decodificar otras codificaciones. El wheel se construyó sin dependencias nuevas y su importación aislada procesó las once unidades de ejemplo. audit/normalization-integration-state.json registra hashes de protección e implementación. Acquisition, REQUISITOS.md y la tesis mantienen sus bytes.

### Correcciones posteriores a la revisión de fidelidad y ámbitos

La revisión del usuario identificó tres defectos reales no cubiertos por la suite inicial: el validador aceptaba texto ajeno a una fuente TXT y cuerpos de diff alterados; aceptaba coordenadas inexistentes de entidades; el extractor trataba funciones locales como métodos del modelo. El hecho de que las 109 pruebas anteriores pasaran no demostraba que esas verificaciones fueran completas.

Se corrigieron los tres casos. validate_collection vuelve a interpretar cada artefacto referenciado una vez por llamada, identifica la parte por localizador completo, tipo y regla, y compara todo el texto y data con la parte canónica. Así respeta transformaciones documentadas de HTML, strings JSON, CRLF y marcadores de falta de salto final en diffs. Cuando se conservaron bytes originales Base64, también comprueba que el texto del artefacto corresponde a su decodificación documentada; no exige hashes nuevos.

Las entidades deben coincidir con las observaciones que esas reglas reconocen en la parte original, incluidos nombre, tipo, contexto, regla y todas sus coordenadas. Se rechazan líneas fuera de rango, coordenadas de tipo incorrecto, lados/rutas de diff falsos y ubicaciones existentes que no respaldan la observación. Los localizadores JSON deben coincidir con rutas canónicas producidas desde la fuente; índices negativos o no canónicos no se aceptan. No se usa una búsqueda literal ingenua del nombre, que rechazaría identificadores válidos codificados mediante escapes Python, XML o JSON.

El visitante Python distingue ámbitos de módulo, clase y función, incluidas funciones async, lambdas y clases anidadas. helper dentro de action conserva su nombre y qualified_name local, model=null y lookup_keys=[]; no genera method:res.partner.helper ni una clave global function:helper. Los métodos directos mantienen sus claves cuando el modelo propietario está explícitamente declarado. Las asignaciones locales _name/_inherit y fields.* no se presentan como declaraciones de modelos o campos de la clase propietaria.

El escritor de colecciones esquema 4 ejecuta ahora la validación contra fuentes antes de crear el archivo SQLite, además de la comprobación coordinada en normalize_session. No se cambió query, BM25, el catálogo ni Acquisition.

Las reglas globales pasan a normalization-2; el esquema de unidad permanece en versión 1 y SQLite en esquema 4. Cambiar reglas cambia legítimamente los IDs derivados. Las colecciones existentes se conservan y siguen siendo legibles; para incorporar las correcciones se reconstruye una colección nueva desde las mismas capturas. No se sobrescriben originales ni bases previas. examples/normalization-units.json se regeneró con las nuevas reglas; la reconstrucción de once unidades, sin incidencias ni relaciones precomputadas, está en temp_data/normalization-review-fixes-20261118/collection.sqlite y report.json.

Verificación de esta corrección: 42 pruebas enfocadas y 129 pruebas generales aprobadas, incluidas veinte regresiones nuevas (trece de fidelidad/coordenadas y siete de ámbitos). Logs: audit/normalization-review-focused-tests.txt y audit/normalization-review-all-tests.txt. Las pruebas alteran contenido, datos del diff y coordenadas, comprueban rechazo antes de escribir SQLite y conservan ejemplos válidos con escapes, CRLF y falta de salto final. audit/normalization-review-fixes.json registra la integridad de archivos protegidos y el estado corregido. La validación acredita fidelidad respecto del artefacto retenido y de las reglas declaradas; no autentica el origen remoto ni demuestra pertinencia o incompatibilidad semántica.

Condición registrada para el siguiente componente: la búsqueda entre information_units y el baseline BM25 deberán compartir exactamente la colección de unidades, revisiones, filtros, consultas y unidad de evaluación. La proyección histórica changes no constituye el mismo universo que documentos, manifiestos y recursos de PR completos. No se presentará una comparación entre universos distintos como evaluación válida. Actualmente retrieve sigue usando changes/elements/relations; su adaptación, las relaciones entre unidades y la memoria permanecen pendientes.

### Límites y trabajo posterior

- Pendiente, fuera de esta tarea: descubrir/recorrer relaciones entre unidades durante la búsqueda y conservar memoria de consultas. No se añadieron rankings nuevos ni recuperación documental nueva.
- Los parsers son deliberadamente acotados: Python estático/fragmentos, XML completo, manifiestos literales y menciones documentales delimitadas; no reconocen toda referencia dinámica ni toda prosa técnica. CSV/shell conservan contenido con advertencia de extracción técnica parcial.
- TXT se conserva completo. RST reconoce encabezados simples. HTML produce una unidad documental; no ofrece localizadores por línea del texto HTML ni un modelo completo de tablas/DOM.
- El diff canónico del PR se usa una sola vez. Patches de archivos se conservan en el original y como referencias; si falta /diff no se inventan cabeceras para patches parciales. Se registra la limitación. Un diff PR malformado no convierte sus comentarios válidos en evidencia de cambio.
- Las reglas y la granularidad no prueban completitud del corpus ni ausencia de incompatibilidades. Los datos de demostración y revisiones simuladas no cuentan como resultados empíricos de la tesis.

## Propuesta histórica: componente unificado de normalización

Estado histórico: esta propuesta describe el diseño previo y la primera consolidación estructural del 2026-11-18. El contrato vigente, el alcance implementado y los pendientes están en «Normalization: backlog y contrato integrado», arriba. Se conserva esta sección para documentar cómo se llegó a ese contrato; sus propuestas pendientes no sustituyen el estado actual.

### Paso 1 realizado: concentrar el procesamiento en normalization

Se sustituyó el archivo r2/normalization.py por el paquete r2/normalization/. La entrada pública normalize_session(inventory, bindings) coordina la lectura y la conversión existentes y devuelve sources, elements, relations, changes, artifacts, documents, warnings y excluded. No descarga ni persiste archivos. collection.build_session consume ahora esa operación y conserva su responsabilidad de almacenamiento y su esquema 3. Los errores de validación continúan propagándose.

| Función trasladada | Responsabilidad e entrada | Salida | Ubicación anterior | Implementación actual |
|---|---|---|---|---|
| normalize(raw, content_type="") | Decodificar bytes UTF-8 y aplicar la limpieza HTML antigua cuando corresponda. | Texto con saltos LF. | r2/normalization.py | r2/normalization/text.py |
| read_session(inventory, bindings) | Leer rutas JSON, validar sesión/unidades/rutas/versiones y cargar artefactos aceptados. | Tupla (units, skipped). | r2/ingestion/session.py | r2/normalization/readers.py |
| convert_units(units) | Interpretar unidades cargadas, separar documentos de contexto y candidatos respaldados por diffs. | Diccionario con sources, elements, relations, changes, artifacts, documents y warnings. | r2/conversion/units.py | r2/normalization/units.py |
| filename(value) | Validar y limpiar una ruta de cabecera de diff. | Ruta relativa o None para /dev/null; ValueError si es inválida. | r2/conversion/diff.py | r2/normalization/diff.py |
| parse_diff(text) | Interpretar y validar texto unified diff, rutas y conteos de líneas. | Tupla (hunks, warnings), con rutas y rangos de cada fragmento. | r2/conversion/diff.py | r2/normalization/diff.py |
| partial_anchors(code, path, module) | Reconocer referencias locales conservadoras en fragmentos Python. | Lista de elementos con ubicación y fundamento de extracción. | r2/conversion/anchors.py | r2/normalization/anchors.py |
| partial_anchors.add(key, kind, name, line) | Auxiliar interno que registra una referencia usando el contexto de partial_anchors. | None; actualiza el diccionario local de elementos. | Interno en r2/conversion/anchors.py | Interno en r2/normalization/anchors.py |

normalize_session es una función nueva en r2/normalization/pipeline.py, no una función trasladada. Los archivos anteriores de ingestion y conversion solo reexportan las mismas funciones para mantener compatibilidad sin lógica duplicada. El import histórico from r2.normalization import normalize permanece válido. El extractor compartido vive en `r2/extract_relations/`.

Límite de esta entrega: la rutina HTML antigua queda disponible por compatibilidad, pero no se incorpora automáticamente al lector de sesiones; este continúa exigiendo UTF-8 como antes. No se agregaron adaptadores, reglas de codificación, atributos de registros, CLI normalize ni cambios en búsqueda. Las propuestas siguientes no se consideran completadas por este traslado.

Verificación: 89 pruebas aprobadas, incluidas cuatro nuevas de compatibilidad, equivalencia del pipeline y propagación de errores. Las seis funciones principales trasladadas conservan el mismo AST, incluido el auxiliar interno. Los once archivos protegidos registrados al inicio (todos los archivos de adquisition, REQUISITOS.md y la tesis) conservan sus hashes. Setuptools descubre el nuevo paquete. Evidencias: [auditoría de traslado](audit/normalization-step1-refactor.json) y [suite general](audit/normalization-step1-tests.txt).

### Decisión posterior del usuario: relaciones entre unidades durante la búsqueda

El usuario decidió que normalización crea unidades de información con atributos y que las relaciones entre esas unidades se descubren y recorren durante la búsqueda. La consulta puede ramificarse hacia distintas fuentes y entre atributos de las propias unidades. Se permite conservar el grafo obtenido después de una búsqueda como memoria reutilizable; no se exige construir previamente el grafo completo del corpus.

Esta decisión sustituye las propuestas anteriores de materializar relaciones entre unidades en conversión. No cambia REQUISITOS.md ni la tesis. No se implementó todavía: convert_units sigue produciendo relaciones extraídas entre elementos técnicos; write_collection las guarda en SQLite; retrieve construye en memoria un grafo a partir de ellas y de las relaciones extraídas del módulo consultado. convert_units no guarda por sí mismo un objeto grafo.

Normalización debe conservar contenido, procedencia, localización, versiones e identificadores explícitamente observados con su evidencia. Extraer un identificador como atributo no debe crear una relación semántica con otra unidad. Las referencias estructurales al artefacto original y sus partes sirven para trazabilidad, sin representar por sí solas caminos de afectación. El esquema final de unidad continúa por definir; no se aprobó aquí una estructura completa nueva.

Para implementar la búsqueda bajo esta decisión, se propone indexar atributos para localizar candidatos sin recorrer todo el corpus, expandir únicamente las unidades alcanzadas y registrar tipo, dirección, regla y evidencia de cada vínculo. La memoria deberá identificarse por colección/revisiones, versión de reglas y condiciones de consulta pertinentes; su reutilización no debe introducir vínculos obsoletos ni perder ramas no exploradas. La política concreta de caché, el esquema, los límites de expansión y las reglas de relación siguen pendientes. No se afirma una mejora de tiempo o espacio sin medirla.

Precisiones del código actual: partial_anchors solo devuelve referencias locales por dos patrones deterministas (self.<opción> en odoo/fields.py u odoo/orm/fields.py, y atributos @nombre dentro de literales .xpath(...)); no genera aristas ni analiza prosa general. normalize_session es un coordinador de lectura/conversión, no un validador completo del esquema futuro de las unidades. Las comprobaciones actuales de read_session validan entradas e integridad y respetan estados de Acquisition; no constituyen una segunda política de admisión.

### Hallazgos previos al traslado estructural

- ingestion/session.py valida unidades/rutas y exige bindings de versiones; solo decodifica UTF-8. Un original Latin-1 admitido por Acquisition termina bloqueado esperando el componente de conversión.
- normalization.py contiene una rutina antigua UTF-8/HTML que aplana contenido y no conserva por sí sola estructura y enlaces suficientemente ricos.
- conversion/units.py conserva el PR completo como artefacto, pero solo interpreta payload.diff. Descripción, comentarios y revisiones carecen de registros propios para consulta.
- Documentación y archivos oficiales ordinarios se conservan como contexto; solo los manifiestos reciben extracción explícita en ese conversor. No hay un contrato uniforme para registros de todos los tipos.
- collection.py y review.search_document indexan cambios con una lista blanca: título, elementos y líneas añadidas/eliminadas. Ese índice no convierte automáticamente todos los documentos o recursos PR en información buscable.
- El parser de diffs, anclas de fragmentos, extractor estático y almacenamiento existen y pueden reutilizarse con límites explícitos.

### Objetivo y frontera

Entrada: inventario y unidades originales admitidas por Acquisition, más metadatos externos cuando sean necesarios. Salida: registros uniformes con texto, atributos, ubicación y procedencia preparados para indexarse. TXT es una exportación de la representación textual; JSON/JSONL conserva el registro y sus atributos.

La lectura, extracción textual y normalización forman una sola operación pública. Internamente habrá adaptadores por formato. No descarga enlaces, no ejecuta código, no analiza el addon del partner para decidir afectación, no expande un grafo, no inventa versiones ni transforma comentarios en diferencias observadas. La cuarentena y las exclusiones no se convierten automáticamente en registros admitidos para búsqueda.

### Pipeline propuesto

1. Leer inventario y validar rutas, archivos y estados. Procesar accepted; registrar lo omitido o problemático sin borrar originales.
2. Resolver la codificación con reglas deterministas y trazables: BOM, metadatos disponibles y UTF-8 estricto; no reemplazar silenciosamente contenido ni adivinar datos ausentes. Reutilizar las reglas comprobadas como utilidad común, evitando dos políticas distintas.
3. Interpretar el formato y producir una representación textual fiel: HTML conserva encabezados, párrafos, listas, tablas, enlaces y código; RST/Markdown mantienen estructura y bloques; código preserva indentación; diffs conservan archivos, cabeceras y rangos; PR desglosa todos sus recursos.
4. Crear registros padre y registros de contenido por límites naturales: documento/sección, archivo/símbolo, archivo de diff/hunk, descripción/comentario/revisión/commit del PR. Cada hijo conserva parent_id y un localizador original. La granularidad concreta debe acordarse antes de implementar; no usar ventanas arbitrarias que rompan código o evidencias.
5. Extraer atributos explícitos y producir el esquema común. Los identificadores técnicos se pueden reconocer estáticamente sin decidir su afectación al partner. Los valores no demostrables se mantienen desconocidos y su procedencia se registra.
6. Preparar search_text y campos filtrables. La creación del índice y la consulta siguen en almacenamiento/recuperación, consumiendo este contrato sin hacer una segunda conversión.
7. Validar integridad, errores por registro y determinismo. Guardar salida y reporte antes de que el coordinador decida borrar temporales. Mantener el original disponible o archivado; normalizar no autoriza eliminarlo.

### Tratamiento por origen/formato

| Entrada | Información propuesta |
|---|---|
| HTML/RST/Markdown/TXT | Título, jerarquía de sección, texto, tablas, enlaces y bloques de código con localizador. |
| Python/XML/CSV/manifiesto | Texto fiel, lenguaje/capa, ruta e identificadores estáticos donde sean demostrables. Shell se conserva como código textual, sin ejecutarlo. |
| Diff | Ruta anterior/nueva, tipo de operación, hunk, rangos, contexto y líneas añadidas/eliminadas; conserva la evidencia original. |
| PR JSON | Descripción, archivos, commits, comentarios, revisiones, comentarios de revisión y diff en registros tipados, enlazados por IDs y recurso. |
| Texto no interpretable o formato no soportado | Diagnóstico y original conservado; no simular un registro completo o indexable. |

Un hunk puede contener varias diferencias y no equivale automáticamente a una incompatibilidad. Las conversaciones y guías son contexto. Los candidatos a cambio siguen necesitando evidencia del diff y revisión de aplicabilidad.

### Registro común propuesto

| Grupo | Campos orientativos |
|---|---|
| Identidad | record_id, parent_id, record_kind, schema_version, normalizer_version. |
| Procedencia | session_id, unit_id, artifact_id, source_kind, URLs y fecha de captura; lista de ocurrencias si hay duplicados exactos. |
| Localización | Ruta original, recurso/ID de PR, sección/XPath o rangos de líneas según el formato. Solo usar coordenadas que se puedan comprobar. |
| Contenido | title, text, language, links y campos específicos: before/after/added/removed para diffs. |
| Contexto técnico | repository, refs/SHAs registrados, versiones declaradas/verificables, capa e identifiers explícitos. Puede haber valores desconocidos. |
| Búsqueda | search_text y atributos filtrables; separa texto de contenido y metadatos administrativos. |
| Calidad | normalization_status, warnings, encoding elegido, métodos de extracción y alcance completo/parcial. |
| Integridad | Identidad del artefacto original y de la representación normalizada, con hashes calculados aquí y alcance explícito. |

Los IDs no dependerían de un UUID nuevo de ejecución o del tiempo de normalización. La procedencia distingue ocurrencias. Se deduplican solo coincidencias exactas cuya identidad esté definida, conservando todas sus fuentes; la equivalencia semántica entre cambios distintos no se decide por similitud textual.

### Organización propuesta

r2/normalization/ sería el único propietario del pipeline: pipeline.py, schema.py, decoding.py, adapters/, records.py y validation.py. Los nombres son orientativos.

- Integrar la lectura útil de ingestion/session.py.
- Mover/adaptar conversion/units.py, diff.py y anchors.py bajo ese componente.
- Reutilizar `r2/extract_relations/` como biblioteca estática compartida; no duplicar reglas.
- Sustituir normalization.py por el paquete y una entrada de compatibilidad para sus consumidores históricos.
- Adaptar collection.build_session para consumir registros normalizados. El índice de registros documentales debe diferenciarse del índice de cambios utilizado por el evaluador actual; no cambiar sus unidades silenciosamente.
- Adaptar la CLI con una operación normalize que permita inspeccionar registros antes de construir el índice. Las antiguas rutas podrán conservar puentes temporales, sin lógica duplicada.

### Secuencia de implementación propuesta

1. Acordar esquema y granularidad con ejemplos reales de cada tipo.
2. Consolidar lector/decodificador/adaptadores y salida de registros en una operación.
3. Incorporar todo el contenido PR y documentación consultable, conservando sus papeles de contexto/evidencia.
4. Integrar persistencia y campos de búsqueda, preservando comparación BM25 y pruebas existentes mediante contratos explícitos.
5. Verificar con las unidades reales ya capturadas y fixtures de formatos/codificaciones que no hayan sido admitidos en las capturas reales.

Criterios propuestos: repetición idéntica de registros para las mismas entradas y versión de normalizador; trazabilidad completa de cada registro al original; ningún recurso PR perdido; código e identificadores preservados; rangos de diff correctos; documentos y comentarios no incrementan contadores de cambios; errores visibles y sin pérdida de originales; ninguna promoción de cuarentena por omisión; compatibilidad o reconstrucción explícita de las colecciones.

Las decisiones de detalle para revisar con el usuario son los tipos de registro, sus atributos obligatorios y la granularidad natural. No se impone una nueva política de relevancia ni una IA para resumir.

## Pendientes conservados del seguimiento anterior

El listado siguiente reproduce íntegro el registro anterior, con sus fuentes y limitaciones. Es una fotografía histórica; algunos puntos se han corregido mediante la autorización actual, según se indique en este documento.

# Pendientes de R2

Este Markdown conserva los pendientes totales y las últimas decisiones para revisarlos uno por uno. Cruza semánticamente las 31 observaciones originales con las 14 decisiones recientes. Según el criterio solicitado, los puntos ausentes de la última lista se consideran corregidos por cruce; esa ausencia no acredita por sí sola una corrección técnica completa. El detalle distingue avances implementados, límites documentados y validación académica pendiente.

## Pendientes totales del listado original

Listado histórico; algunos puntos ya tienen avances o correcciones.

- **T01.** Unificar la documentación histórica y vigente de entrega.
- **T02.** Implementar la recolección mediante la API REST de GitHub.
- **T03.** Integrar las descargas documentales con el constructor de R2.
- **T04.** Registrar fechas de captura y procedencia de las fuentes.
- **T05.** Completar el corpus de los tres saltos de versión.
- **T06.** Validar el corte temporal y los seis criterios de selección.
- **T07.** Normalizar los XML-ID locales por módulo.
- **T08.** Representar las llamadas entre plantillas QWeb.
- **T09.** Construir relaciones semánticas de seguridad desde CSV.
- **T10.** Distinguir campos y métodos al resolver referencias Python.
- **T11.** Exigir evidencia estructurada de vigencia para cambios verificados.
- **T12.** Permitir relaciones múltiples entre evidencias y cambios semánticos.
- **T13.** Comprobar la generalización con casos reales de construcción.
- **T14.** Distinguir hashes de bytes originales y texto normalizado.
- **T15.** Ratificar las semillas de hallazgos directos e indirectos.
- **T16.** Acreditar la ejecución efectiva de NetworkX.
- **T17.** Conservar todas las evidencias de cada arista.
- **T18.** Calibrar la pertinencia del ordenamiento con casos de construcción.
- **T19.** Distinguir candidatos y cambios verificados en resultados y contadores.
- **T20.** Mostrar elementos, versiones y evidencias completas en la salida textual.
- **T21.** Justificar y congelar los campos documentales de BM25.
- **T22.** Reproducir los parámetros de consulta desde el evaluador.
- **T23.** Resolver el uso metodológico de pandas, scikit-learn y statsmodels.
- **T24.** Validar estado, salto y elemento en las correspondencias de C1.
- **T25.** Reportar separadamente hallazgos pertinentes ausentes del MIG.
- **T26.** Completar la revisión lingüística y autenticidad de evidencias para V1.
- **T27.** Ratificar el límite operacional de T1.
- **T28.** Controlar orden experimental, repeticiones y caché.
- **T29.** Ampliar las pruebas sobre importación, identidades, relaciones y versiones.
- **T30.** Delimitar el alcance probatorio del piloto histórico.
- **T31.** Completar la evaluación independiente y verificar los indicadores de tesis.

## Últimos pendientes

- **P01.** Elegir el modelo y snapshot de R4.
- **P02.** Confirmar el corte documentado y la fecha de separación experimental.
- **P03.** Definir las fuentes generales posteriores al corte admisibles en R2.
- **P04.** Designar al responsable de revisar los seis criterios de selección.
- **P05.** Designar al responsable de los juicios de pertinencia y cobertura.
- **P06.** Designar al responsable de revisar el inglés de las salidas.
- **P07.** Fijar los repositorios y revisiones del corpus de construcción.
- **P08.** Ratificar la definición de consultas y semillas de profundidad cero.
- **P09.** Fijar la profundidad máxima del recorrido.
- **P10.** Calibrar y congelar el ordenamiento utilizando exclusivamente casos de construcción.
- **P11.** Ratificar P1 como promedio de consultas con precisión definida.
- **P12.** Elegir el límite operacional de T1.
- **P13.** Fijar las repeticiones y condiciones de caché para medir tiempos.
- **P14.** Resolver la discrepancia metodológica sobre statsmodels en R2.

## Resueltos o corregidos según el cruce

Veinte puntos originales no aparecen temáticamente en las decisiones recientes. Los matices de cierre se conservan en el detalle.

- **C01 / T01.** La entrega distingue la documentación vigente del material histórico.
- **C02 / T02.** La recolección incorpora la API REST de GitHub.
- **C03 / T03.** Las capturas documentales alimentan una colección reconstruible.
- **C04 / T04.** Las capturas registran procedencia temporal y hashes.
- **C07 / T07.** Los XML-ID locales se normalizan por módulo.
- **C08 / T08.** Las plantillas QWeb incluyen relaciones de llamada.
- **C09 / T09.** La extracción representa relaciones de seguridad.
- **C10 / T10.** La resolución estática distingue campos, métodos y referencias pendientes.
- **C11 / T11.** Las revisiones incluyen condiciones y vigencia del salto.
- **C12 / T12.** Cambios y evidencias admiten enlaces múltiples.
- **C14 / T14.** Los hashes distinguen bytes originales y texto normalizado.
- **C16 / T16.** La ejecución efectiva de NetworkX tiene registros separados.
- **C17 / T17.** Las aristas conservan múltiples evidencias.
- **C19 / T19.** Los resultados distinguen candidatos y cambios verificados.
- **C20 / T20.** La presentación amplía la información explícita de cada hallazgo.
- **C22 / T22.** El evaluador explicita los parámetros de consulta.
- **C24 / T24.** C1 incorpora controles de correspondencia y aplicabilidad.
- **C25 / T25.** Los hallazgos pertinentes fuera del MIG se reportan separadamente.
- **C29 / T29.** La suite amplía las pruebas técnicas del sistema.
- **C30 / T30.** Los límites del piloto histórico están documentados.

## Detalle de todas las listas

### Detalle del listado total

#### T01. Unificar la documentación histórica y vigente de entrega.

Observación original: La carpeta revision corresponde a una etapa previa del sistema. Describe R2 como no implementado y al selector como independiente; el paquete posterior ya incorpora esas funciones. Es necesario unificar la documentación de entrega.

Cruce: ausente de las decisiones recientes; clasificado como C01. Véase el alcance de corrección al final.

#### T02. Implementar la recolección mediante la API REST de GitHub.

Observación original: La API REST de GitHub definida en la Tabla 4 no está implementada en R2. La recolección admite Git local y snapshots, pero no obtiene metadatos de PR, revisiones ni criterios de selección mediante esa API.

Cruce: ausente de las decisiones recientes; clasificado como C02. Véase el alcance de corrección al final.

#### T03. Integrar las descargas documentales con el constructor de R2.

Observación original: Los descargadores de documentación están separados del constructor R2. Generan archivos e inventarios, pero no los convierten directamente en fuentes del manifiesto que consume el paquete.

Cruce: ausente de las decisiones recientes; clasificado como C03. Véase el alcance de corrección al final.

#### T04. Registrar fechas de captura y procedencia de las fuentes.

Observación original: Las descargas usan direcciones mutables. Conservan SHA256 de la copia, pero sus registros no incluyen una fecha de captura ni una revisión upstream fijada. El hash identifica lo descargado; falta completar su procedencia temporal.

Cruce: ausente de las decisiones recientes; clasificado como C04. Véase el alcance de corrección al final.

#### T05. Completar el corpus de los tres saltos de versión.

Observación original: La colección de demostración cubre únicamente dos archivos del núcleo para 16→17. No acredita el alcance de fuentes y saltos 16→17, 17→18 y 18→19 previsto para R2.

Cruce: conserva relación con P03, P07. Su cierre requiere resolver esas decisiones y completar la ejecución o revisión correspondiente.

#### T06. Validar el corte temporal y los seis criterios de selección.

Observación original: La exclusión de evaluación depende de metadatos declarados. El selector aplica correctamente split y la procedencia transitiva, pero no comprueba el corte temporal ni los seis criterios de selección de la tesis.

Cruce: conserva relación con P01, P02, P04. Su cierre requiere resolver esas decisiones y completar la ejecución o revisión correspondiente.

#### T07. Normalizar los XML-ID locales por módulo.

Observación original: Los XML-ID locales no se normalizan con el nombre del módulo. Una declaración view_order_form puede quedar separada de una referencia sale_advance_payment.view_order_form; también pueden coincidir identificadores locales de módulos distintos.

Cruce: ausente de las decisiones recientes; clasificado como C07. Véase el alcance de corrección al final.

#### T08. Representar las llamadas entre plantillas QWeb.

Observación original: Las llamadas QWeb t-call se registran como elementos, sin una relación de llamada. Esto limita el recorrido entre plantillas.

Cruce: ausente de las decisiones recientes; clasificado como C08. Véase el alcance de corrección al final.

#### T09. Construir relaciones semánticas de seguridad desde CSV.

Observación original: La extracción CSV recoge identificadores, pero no construye sus relaciones semánticas. Falta representar de forma explícita relaciones de seguridad con modelos y grupos.

Cruce: ausente de las decisiones recientes; clasificado como C09. Véase el alcance de corrección al final.

#### T10. Distinguir campos y métodos al resolver referencias Python.

Observación original: Una referencia self.x puede generar una relación hacia un método aunque x sea un campo. El extractor no resuelve suficientemente esa distinción antes de crear self_reference.

Cruce: ausente de las decisiones recientes; clasificado como C10. Véase el alcance de corrección al final.

#### T11. Exigir evidencia estructurada de vigencia para cambios verificados.

Observación original: La categoría verified exige responsable y justificación, pero no evidencia estructurada de vigencia en destino. La revisión puede aceptarse sin registrar por separado cómo se comprobó la aplicabilidad a la versión destino.

Cruce: ausente de las decisiones recientes; clasificado como C11. Véase el alcance de corrección al final.

#### T12. Permitir relaciones múltiples entre evidencias y cambios semánticos.

Observación original: Se permite agrupar varios fragmentos en un cambio, pero no dividir explícitamente un mismo fragmento en varios cambios semánticos. El modelo no representa completamente esa relación entre evidencia y cambio.

Cruce: ausente de las decisiones recientes; clasificado como C12. Véase el alcance de corrección al final.

#### T13. Comprobar la generalización con casos reales de construcción.

Observación original: El reconocimiento de ciertos cambios está especializado en nombres del ejemplo. attrs, states, invisible, readonly y t-call reciben tratamiento explícito; falta comprobar su generalización con otros casos de construcción.

Cruce: conserva relación con P10. Su cierre requiere resolver esas decisiones y completar la ejecución o revisión correspondiente.

#### T14. Distinguir hashes de bytes originales y texto normalizado.

Observación original: Los hashes de archivos se calculan sobre texto decodificado o normalizado. Deben distinguirse de los hashes de los bytes originales para evitar atribuirles una trazabilidad que no representan.

Cruce: ausente de las decisiones recientes; clasificado como C14. Véase el alcance de corrección al final.

#### T15. Ratificar las semillas de hallazgos directos e indirectos.

Observación original: Todos los elementos extraídos se utilizan como semillas de profundidad cero. Incluye referencias encontradas en el módulo. La convención debe fijarse metodológicamente porque cambia la interpretación de hallazgos directos e indirectos.

Cruce: conserva relación con P08, P09. Su cierre requiere resolver esas decisiones y completar la ejecución o revisión correspondiente.

#### T16. Acreditar la ejecución efectiva de NetworkX.

Observación original: NetworkX está implementado, pero su ejecución no está garantizada. Si falta la biblioteca, se usa otro BFS. En las pruebas que ejecuté se utilizó stdlib_bfs_fallback; esa ejecución no acredita el uso efectivo de NetworkX.

Cruce: ausente de las decisiones recientes; clasificado como C16. Véase el alcance de corrección al final.

#### T17. Conservar todas las evidencias de cada arista.

Observación original: Cuando varias fuentes respaldan la misma arista, el grafo conserva una sola evidencia. La condición not graph.has_edge(...) impide añadir los respaldos posteriores a esa arista.

Cruce: ausente de las decisiones recientes; clasificado como C17. Véase el alcance de corrección al final.

#### T18. Calibrar la pertinencia del ordenamiento con casos de construcción.

Observación original: El ordenamiento es reproducible, pero su pertinencia no está calibrada con casos reales de construcción. Tener reglas deterministas no demuestra que los primeros resultados sean los más relevantes.

Cruce: conserva relación con P10. Su cierre requiere resolver esas decisiones y completar la ejecución o revisión correspondiente.

#### T19. Distinguir candidatos y cambios verificados en resultados y contadores.

Observación original: La consulta mezcla candidatos y verificados por defecto. El resumen cuenta ambos; debe distinguirlos para que “cambios encontrados” no se interprete como cambios confirmados.

Cruce: ausente de las decisiones recientes; clasificado como C19. Véase el alcance de corrección al final.

#### T20. Mostrar elementos, versiones y evidencias completas en la salida textual.

Observación original: La vista textual omite información explícita por hallazgo. No presenta claramente el elemento afectado y las versiones origen/destino; en agrupaciones tampoco muestra todos los bloques de evidencia. El JSON contiene más información.

Cruce: ausente de las decisiones recientes; clasificado como C20. Véase el alcance de corrección al final.

#### T21. Justificar y congelar los campos documentales de BM25.

Observación original: BM25 indexa el registro JSON completo. Incluye contenido de evidencia junto con metadatos y datos de revisión, que también pueden influir en el ranking. Falta justificar y congelar los campos documentales indexados.

Cruce: conserva relación con P07, P10. Su cierre requiere resolver esas decisiones y completar la ejecución o revisión correspondiente.

#### T22. Reproducir los parámetros de consulta desde el evaluador.

Observación original: El evaluador no permite reproducir todos los parámetros de consulta. No transmite un filtro de estado ni un límite configurable; utiliza los valores predeterminados de retrieve().

Cruce: ausente de las decisiones recientes; clasificado como C22. Véase el alcance de corrección al final.

#### T23. Resolver el uso metodológico de pandas, scikit-learn y statsmodels.

Observación original: No se utilizan pandas, scikit-learn ni statsmodels, aunque aparecen asignados a R2 en la Tabla 4. Las métricas se calculan con Python estándar. Hay que justificar la sustitución o ajustar la implementación según una función metodológica pertinente.

Cruce: conserva relación con P14. Su cierre requiere resolver esas decisiones y completar la ejecución o revisión correspondiente.

#### T24. Validar estado, salto y elemento en las correspondencias de C1.

Observación original: C1 verifica que los cambios citados existan, pero no comprueba su estado, salto y elemento. Una correspondencia humana puede apuntar a un cambio candidato o inadecuado sin que el evaluador la rechace por esos motivos.

Cruce: ausente de las decisiones recientes; clasificado como C24. Véase el alcance de corrección al final.

#### T25. Reportar separadamente hallazgos pertinentes ausentes del MIG.

Observación original: Los hallazgos pertinentes ausentes del MIG no se reportan en una categoría diferenciada. El evaluador permite pertinencia sin vinculación a referencias, pero no genera el registro separado previsto en la tesis.

Cruce: ausente de las decisiones recientes; clasificado como C25. Véase el alcance de corrección al final.

#### T26. Completar la revisión lingüística y autenticidad de evidencias para V1.

Observación original: V1 comprueba solo parte de la conformidad exigida. Valida campos y algunas consistencias, pero no el idioma de los textos ni la autenticidad completa de las evidencias contra las fuentes.

Cruce: conserva relación con P05, P06. Su cierre requiere resolver esas decisiones y completar la ejecución o revisión correspondiente.

#### T27. Ratificar el límite operacional de T1.

Observación original: T1 termina antes de validar, serializar e imprimir la salida. Actualmente representa tiempo interno de recuperación y preparación del resultado; no todo el tiempo hasta presentar la primera vista y el resumen en la CLI.

Cruce: conserva relación con P12. Su cierre requiere resolver esas decisiones y completar la ejecución o revisión correspondiente.

#### T28. Controlar orden experimental, repeticiones y caché.

Observación original: El evaluador ejecuta primero las repeticiones del grafo y después las de BM25. No alterna el orden y admite caché declarada como uncontrolled; falta controlar estas condiciones para comparar tiempos.

Cruce: conserva relación con P13. Su cierre requiere resolver esas decisiones y completar la ejecución o revisión correspondiente.

#### T29. Ampliar las pruebas sobre importación, identidades, relaciones y versiones.

Observación original: Las once pruebas no cubren varias brechas relevantes. Predominan snapshots sintéticos; faltan pruebas del importador con Git real, identidades entre módulos, relaciones QWeb y seguridad, y casos representativos de los tres saltos.

Cruce: ausente de las decisiones recientes; clasificado como C29. Véase el alcance de corrección al final.

#### T30. Delimitar el alcance probatorio del piloto histórico.

Observación original: El piloto histórico no demuestra una migración autónoma ni equivalencia funcional. Reutilizó código previamente adaptado y ejecutó las pruebas en una base diferente de la actualizada. Sus tiempos tampoco corresponden al T1 de consulta R2.

Cruce: ausente de las decisiones recientes; clasificado como C30. Véase el alcance de corrección al final.

#### T31. Completar la evaluación independiente y verificar los indicadores de tesis.

Observación original: La evaluación independiente de tesis sigue pendiente. No se ha acreditado la muestra de 30 MIG, los juicios definitivos ni el cumplimiento de C1 o la diferencia de precisión frente a BM25.

Cruce: conserva relación con P01, P02, P04, P05, P06, P07, P11. Su cierre requiere resolver esas decisiones y completar la ejecución o revisión correspondiente.

### Detalle de los últimos pendientes

#### P01. Elegir el modelo y snapshot de R4.

Identificar proveedor, modelo y snapshot exacto. El usuario confirmó que aún no están definidos.

#### P02. Confirmar el corte documentado y la fecha de separación experimental.

Documentar el corte de entrenamiento y la frontera entre construcción y evaluación. Agosto de 2025 sigue siendo ilustrativo.

#### P03. Definir las fuentes generales posteriores al corte admisibles en R2.

Precisar qué documentación general posterior al corte se permite, especialmente para 18→19; distinguirla de migraciones reservadas.

#### P04. Designar al responsable de revisar los seis criterios de selección.

Revisar mantenedor independiente, módulo único, versiones consecutivas, pruebas automatizadas, dependencias comunitarias públicas y ausencia de FIX de comportamiento.

#### P05. Designar al responsable de los juicios de pertinencia y cobertura.

Asignar revisores reales para pertinencia, correspondencias y cobertura; completar los juicios independientes antes de evaluar.

#### P06. Designar al responsable de revisar el inglés de las salidas.

Completar la revisión humana del inglés. La validación estructural automática no acredita conformidad lingüística.

#### P07. Fijar los repositorios y revisiones del corpus de construcción.

Delimitar repositorios, revisiones o capturas, alcance, exclusiones y codificación. Nueve unidades parciales no constituyen el corpus completo.

#### P08. Ratificar la definición de consultas y semillas de profundidad cero.

Definir qué declaraciones y referencias constituyen semillas y cómo se interpreta la distancia de cada hallazgo.

#### P09. Fijar la profundidad máxima del recorrido.

Determinar el límite de BFS y registrarlo en el protocolo congelado.

#### P10. Calibrar y congelar el ordenamiento utilizando exclusivamente casos de construcción.

Ajustar reglas, prioridades y desempates con construcción. Congelar también los campos documentales de BM25 antes de evaluar.

#### P11. Ratificar P1 como promedio de consultas con precisión definida.

Confirmar agregación macro y tratamiento de consultas sin precisión definida; conservar resultados y denominadores individuales.

#### P12. Elegir el límite operacional de T1.

Elegir entre hasta validación y serialización o hasta completar stdout de la CLI. Conservar separadas las otras medidas.

#### P13. Fijar las repeticiones y condiciones de caché para medir tiempos.

Definir repeticiones, calentamiento, caché y entorno; mantener orden contrabalanceado y medidas individuales.

#### P14. Resolver la discrepancia metodológica sobre statsmodels en R2.

pandas y scikit-learn ya se ejecutaron con funciones concretas. statsmodels está instalado, pero no se usó sin inferencia justificada.

### Detalle de los puntos corregidos por cruce

#### C01. La entrega distingue la documentación vigente del material histórico.

Procedencia: T01. No se afirma haber reescrito toda la carpeta externa revision.

#### C02. La recolección incorpora la API REST de GitHub.

Procedencia: T02. La API se ejecutó. La ampliación reciente recibió HTTP 403; la selección completa sigue pendiente.

#### C03. Las capturas documentales alimentan una colección reconstruible.

Procedencia: T03. La colección documental actual tiene inventario y reconstrucción offline; los descargadores antiguos son antecedentes.

#### C04. Las capturas registran procedencia temporal y hashes.

Procedencia: T04. Una captura mutable no se presenta como commit upstream. No se inventaron revisiones.

#### C07. Los XML-ID locales se normalizan por módulo.

Procedencia: T07. El informe registra normalización e identidades separadas entre módulos.

#### C08. Las plantillas QWeb incluyen relaciones de llamada.

Procedencia: T08. El informe registra llamadas y herencia QWeb.

#### C09. La extracción representa relaciones de seguridad.

Procedencia: T09. El informe registra referencias de grupos, datos y seguridad.

#### C10. La resolución estática distingue campos, métodos y referencias pendientes.

Procedencia: T10. Las referencias no resueltas conservan ese estado, sin inventar un método.

#### C11. Las revisiones incluyen condiciones y vigencia del salto.

Procedencia: T11. La estructura está implementada; el corpus general todavía carece de revisión independiente.

#### C12. Cambios y evidencias admiten enlaces múltiples.

Procedencia: T12. El modelo incorpora enlaces M:N para agrupación y división semántica.

#### C14. Los hashes distinguen bytes originales y texto normalizado.

Procedencia: T14. Cada representación conserva su identidad; no se atribuye al texto el hash de bytes.

#### C16. La ejecución efectiva de NetworkX tiene registros separados.

Procedencia: T16. Hay registros con NetworkX real, compatibilidad y segundo entorno limpio.

#### C17. Las aristas conservan múltiples evidencias.

Procedencia: T17. La prueba de recorrido indirecto conserva varios respaldos sobre una arista.

#### C19. Los resultados distinguen candidatos y cambios verificados.

Procedencia: T19. Los 432 fragmentos candidatos no se presentan como 432 incompatibilidades verificadas.

#### C20. La presentación amplía la información explícita de cada hallazgo.

Procedencia: T20. La aceptación lingüística sigue pendiente; este cruce no certifica por sí solo cada requisito visual.

#### C22. El evaluador explicita los parámetros de consulta.

Procedencia: T22. Estado, límite y profundidad son parámetros compartidos y reproducibles.

#### C24. C1 incorpora controles de correspondencia y aplicabilidad.

Procedencia: T24. Se comprueban salto, elemento, vigencia y condiciones además de la existencia del cambio.

#### C25. Los hallazgos pertinentes fuera del MIG se reportan separadamente.

Procedencia: T25. Su ausencia del MIG no implica automáticamente un falso positivo.

#### C29. La suite amplía las pruebas técnicas del sistema.

Procedencia: T29. Hay 33 casos bajo tres condiciones. No son 99 requisitos ni demuestran representatividad académica completa.

#### C30. Los límites del piloto histórico están documentados.

Procedencia: T30. Se corrigió su interpretación. No se ejecutó otra migración autónoma ni se acreditó equivalencia funcional.

### Fuentes y límites

- Fuente original: adjunto d97080b3-b253-49b5-8617-f6af55f7fff6/Texto pegado.txt, con 31 observaciones.
- Fuente reciente: respuesta anterior con 14 decisiones, conservadas en significado.
- Estado consultado: [Informe de cumplimiento](audit/INFORME_CUMPLIMIENTO.md).
- Cruce: 11 observaciones relacionadas con decisiones recientes y 20 ausentes, clasificadas como corregidas.
- El corpus sigue parcial y sin codificación independiente completa. La evaluación final y los treinta MIG elegibles continúan pendientes.
- El piloto histórico conserva sus limitaciones. Documentarlas no equivale a haberlas eliminado experimentalmente.
- Este registro no modifica la tesis ni acredita resultados académicos nuevos.

## 2026-11-19 — Traslado del extractor estático compartido

La implementación de 266 líneas pasó a `r2/extract_relations/core.py` con el mismo SHA-256. La API pública se declara en `r2/extract_relations/__init__.py`. Se retiró el módulo anterior `r2.extract` y se eliminó su caché Python 3.12. Los consumidores externos deben importar desde `r2.extract_relations`.

Se actualizaron ocho sentencias de import en `r2/query.py`, `r2/cli.py`, `r2/collection.py`, `r2/normalization/anchors.py`, `r2/normalization/entities.py`, `tests/test_r2.py` y `tests/test_methodology.py`. Se actualizaron dos referencias de este documento y una en `r2/crossing/README.md`.

Pasaron 164 pruebas antes y después del traslado. La CLI respondió a `--version` y `doctor`. Se regeneraron `build/lib/r2/` y el manifiesto de fuentes, y se comprobó el import público directamente desde el wheel reconstruido sin dependencias. Los registros de la línea base y de la ejecución final quedaron en `.cache/extract-relations-refactor/`. Los archivos históricos protegidos conservan sus hashes.

## 2026-11-19 — Integración de los componentes y prueba de CLI

La lógica de almacenamiento de colección pasó a `r2/conversion/storage.py`. La consulta y la revisión pasaron a `r2/filter_ordering/`. El grafo histórico quedó en `r2/relations/legacy_graph.py` y la extracción de relaciones entre unidades se integró en `r2/relations/` con operaciones distintas de identificación y recorrido. Las funciones de evaluación y selección están en `r2/evaluation/`. La política histórica de fuentes está en `r2/adquisition/legacy_policy.py` y el extractor CSV compartido en `r2/extract_relations/csv_entities.py`. Los módulos antiguos conservan importaciones de compatibilidad para consumidores actuales; `r2/extract.py` sigue retirado según el cambio anterior.

La CLI incorpora `extract-relations` para consumir un resultado de cruce y `search-units` para ejecutar cruce y extracción de relaciones en orden. La suite completa y la prueba del CLI documentan el comportamiento. `examples/run_evaluation_demo.py` ejecuta el evaluador existente con juicios sintéticos y `--development`. Su reporte en `temp_data/evaluation-cli-demo/metrics/report.json` verifica la ruta de ingeniería, pero no representa evaluación académica. C1 y C2 permanecen indefinidos sin las referencias y revisiones externas requeridas.
