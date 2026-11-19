# Requisitos del proyecto R2

Documento global de requisitos. Creado el 17 de noviembre de 2026 por instrucción explícita del usuario. **Solo debe editarse cuando el usuario lo indique expresamente.** Los avances, resultados de pruebas, interpretaciones de implementación y pendientes se registran en CONTEXTO_PROYECTO.md, sin modificar este archivo.

## Autoridad y lectura

Las aclaraciones más recientes del usuario prevalecen sobre los textos históricos incorporados literalmente al final. Los bloques originales se preservan sin reescritura; sus estados y propuestas antiguas no describen por sí solos la implementación actual. La tesis Word no se modifica mediante este documento. Si aparece una contradicción o falta una decisión, debe registrarse en contexto, no resolverse inventando un requisito.

## Aclaraciones vigentes del usuario: transcripción literal

### Origen de enlaces y control documental

> estos enlaces los hace otro componente, registralo porfa en algún md global de donde saques tus especificaciones (reducelos todos a 2, uno con los requisitos tal cual y otro con el contexto del proyecto y el primero solo editalo cuando te diga)

### Fuentes

Selección comentada: «2. Cubrir cada origen».

> si

Plan al que corresponde la aprobación:

> Admitir documentos, archivos, diffs y PR de esas fuentes. Identificar expresamente cualquier formato todavía no soportado.

### Descarga e interpretación

Selección comentada: «Separar descarga e interpretación».

> si, por definir ccomo se va a pasar esto a texto

### Codificaciones

> quiero que la codificación no falle, haz algo para ello

### Exclusión

Selección comentada: «5. Evitar bloqueos incorrectos».

> es cierto este de acquisition debe rechazar este tipo de unidades

### Fallos de acceso

Selección comentada: «. Gestionar fallos de acceso».

> si

Plan al que corresponde la aprobación:

> Registrar errores, aplicar reintentos cuando corresponda y continuar el lote. Ninguna fuente fallida debe quedar oculta.

### Pruebas reales

Selección comentada: «Probar cada origen realmente».

> si

Plan al que corresponde la aprobación:

> Descargar contenido real de las cuatro familias, comprobar sus archivos e inventarios y probar caché y borrado.

### Confirmación de ejecución

> sí dale, con eso queda

### Frontera con el componente siguiente

> esto es parte del alcance, debe descargar toooodo y luego el siguiente componente hace esta exploración. Aunque sí debe jalar de varias fuentes. de qué fuentes terminó extrayendo datos? de qué urls?

> esas relaciones serán con otro componente

### Naturaleza del sistema

> esta herramienta es determinista por si acaso, no se conecta con la ia para hacer la búsqueda

## Contrato original de Acquisition: copia literal de referencia

Fuente: reference/adquisition-final/backlog_adquisition.md. Se conserva íntegro para trazabilidad. Las aclaraciones anteriores autorizan separar la interpretación textual, conservar originales y corregir codificaciones, por lo que las descripciones antiguas de conversión HTML/TXT y versión final inmutable deben leerse históricamente.

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


## Requisitos iniciales de R2: copia literal de referencia

Fuente original: BACKLOG.md, conservado en archive/specifications-pre-20261117/BACKLOG.md. El siguiente bloque reproduce contrato, herramientas e historias iniciales; la implementación y los estados actualizados se consultan en CONTEXTO_PROYECTO.md. Las decisiones posteriores sobre adquisición, política y separación de componentes prevalecen.

# Backlog de R2

Fecha: 13 de noviembre de 2026. Alcance: R2.1 base local de información de migración y R2.2 CLI determinista en inglés. Este backlog se redacta antes de implementar el programa. Estado inicial: solo existían el mapeo exploratorio y un selector de fuentes independiente.

## Contrato del resultado

R2 lee el módulo original sin ejecutarlo ni modificarlo. Recoge diferencias entre estados fijados por revisión, conserva evidencias, cruza elementos Odoo, recorre relaciones y devuelve hasta diez cambios con fuentes, caminos, profundidad mínima y resumen. No utiliza IA, embeddings, servicios de LLM ni generación de resúmenes por modelos. Los textos explicativos proceden de evidencia o anotaciones verificables; los resúmenes son contadores deterministas. R2 no migra módulos, calcula horas ni declara equivalencia funcional.

## Métodos y herramientas de la tesis

| Elemento | Aplicación prevista en esta entrega | Declaración de alcance |
|---|---|---|
| Ciencia del diseño, Hevner et al. (2004) | Artefacto ejecutable, requisitos y comprobaciones reproducibles | No equivale a haber completado la evaluación de tesis |
| Python 3.12 | Paquete y CLI, sin ejecutar código de módulos analizados | Lenguaje de implementación y verificación |
| Git | Leer árboles fijados por SHA y generar diffs sin depender de mensajes MIG/FIX | Repositorios locales; descarga explícita mediante Git separada de consulta |
| API REST de GitHub | Recolección opcional de metadatos de PR | Pendiente en esta entrega; no necesaria para consultar o importar Git local |
| Análisis de contenido | Capa, versión, elementos, evidencia, categoría y validación | Extracción determinista; revisión de aplicabilidad mediante anotaciones explícitas |
| ast | Identificar modelos, clases, campos, métodos, dependencias, referencias y manifiestos | La Tabla 4 lo asigna a R4; se reutiliza también para lectura en R2 |
| lxml y XPath | Leer vistas/QWeb y referencias sin resolver entidades externas | También se reutiliza de R4; no valida la arquitectura final de Odoo |
| NetworkX y bfs_layers | Recorrido multiorigen por niveles, sin duplicar por ciclos | Profundidad mínima y camino estable; profundidad máxima declarada |
| BM25, Thakur et al. (2021) | Baseline FTS5 sobre los mismos cambios, filtros y consulta | Sin expansión por relaciones; tokenización y parámetros documentados |
| Elastic Ranking evaluation | Juicios explícitos por consulta y unidad de cambio | Método de evaluación; no se instala Elasticsearch |
| pandas | Tablas del evaluador | No necesario en el núcleo; inicialmente se usan csv/json estándar y se declara la sustitución |
| scikit-learn | Métricas | No utilizado: fórmulas explícitas para respetar vacíos/no aplicables |
| statsmodels | Intervalos y contraste de otros resultados | No utilizado en R2; no aplicar McNemar ni Wilson por defecto a entradas dependientes |
| LibCST | Transformación conservando formato | No utilizado: R2 no transforma código |
| Odoo Community, PostgreSQL, Docker | Laboratorio de funcionamiento/ejecución del programa | R2 no necesita un servidor Odoo ni PostgreSQL; Docker permite verificar con Python 3.12 disponible |
| upgrade-util, pylint-odoo, cloc | R3/R1 | No utilizados por este programa R2 |
| upgrade_code y odoo-module-migrator | R1/R4, evidencias potenciales | No se ejecutan para transformar módulos en R2 |
| Modelo de lenguaje/RAG | Consumidor externo de la salida en R4 | No utilizado dentro de R2 |
| Muestreo estratificado de 30 migraciones | Evaluación independiente final | Pendiente; ninguna demostración local acredita C1 ≥ 90 % |

## Complementos de ingeniería

SQLite conserva una colección local reconstruible; FTS5 implementa BM25. argparse expone CLI; JSON define el contrato, JSONL las consultas y exportaciones, hashlib verifica contenido, difflib compara snapshots y ast/csv leen entradas. unittest verifica comportamientos relevantes. Son complementos propuestos, no selecciones originalmente escritas en la tesis.

## Historias y criterios de aceptación

| ID | Trabajo | Criterio de aceptación | Estado inicial |
|---|---|---|---|
| R2-01 | Paquete, CLI y esquema | Instalación Python 3.12, ayuda en inglés y salida JSON con versión | Por hacer |
| R2-02 | Recolección de fuentes | Git local fijado a commits; snapshots con SHA256; ninguna lectura implícita de HEAD cambiante | Por hacer |
| R2-03 | Exclusión MIG/FIX | Desactivada por defecto, exclusión transitiva, referencias de evaluación siempre fuera del índice | Selector previo existe; integrar |
| R2-04 | Extracción de información | Python/XML/CSV/manifiesto; ubicación y avisos para sintaxis no analizable | Por hacer |
| R2-05 | Conversión de información | Comparaciones, bloques del diff, elementos, relaciones y cambios separados; no deducir un cambio de un título | Por hacer |
| R2-06 | Persistencia y trazabilidad | SQLite y exportación canónica; consulta de detalle con evidencia antes/después | Por hacer |
| R2-07 | Cruce | Identidad Odoo exacta, referencias explícitas y advertencias de dinámica no resuelta | Por hacer |
| R2-08 | Extracción/recorrido de relaciones | BFS multiorigen, ciclos, camino estable y profundidad mínima | Por hacer |
| R2-09 | Filtro y ordenamiento | Salto/capa, prioridad estable, filtros de candidatos o verificados, máximo diez | Por hacer |
| R2-10 | Presentación | Changes found/shown, Matching migrations, Methods with documented changes, Changes by layer, New findings by depth | Por hacer |
| R2-11 | Línea base BM25 | Misma unidad/corpus/consulta; no usa grafo | Por hacer |
| R2-12 | Evaluador | C1/P1/C2/V1/T1 con juicios explícitos; vacíos y N/A; tiempos de preparación separados | Por hacer |
| R2-13 | Verificación integral | Flujo real de importación/consulta/exportación y pruebas de fugas, versiones, ciclos, límites y XML/Python | Por hacer |
| R2-14 | Documentación y ejemplo local | Comandos reproducibles, arquitectura, límites, política y ejemplo sin soluciones MIG/FIX | Por hacer |
| R2-15 | Corpus oficial 16–19 completo | Inventario revisado, cobertura, relaciones auditadas y evaluación de 30 casos | Pendiente posterior al prototipo |
| R2-16 | Piloto de migración desde copia idéntica | Comprobación de origen intacto y adaptación registrada desde cero | Trabajo posterior de laboratorio; no requisito de consulta R2 |

