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

## Reglas de evaluación e independencia

El modo de fuentes forma parte de la identidad de colección. No se cambia un flag sobre una base contaminada: se reconstruye. El conjunto reservado se mantiene fuera del programa de consulta; solo el evaluador lee juicios y correspondencias. El interruptor excluye contenido derivado declarado, no solo etiquetas; no puede descubrir procedencia falsa. Los ejemplos inspeccionados al desarrollar quedan fuera de evaluación final. Las referencias externas permitidas deben congelarse antes de medir y auditarse para evitar copias de soluciones reservadas.

Un bloque del diff es evidencia, no una unidad semántica perfecta. La extracción automática genera candidatos; las anotaciones verificadas pueden agrupar bloques y proporcionar condiciones explícitas, siempre citando una comparación real. Se informa el estado y no se llama incompatibilidad confirmada a toda diferencia textual.

La primera vista no se usa como sinónimo de toda la base: C1 y C2 tienen denominadores distintos. V1 comprueba campos, límites, contadores, caminos y trazabilidad. T1 incluye análisis de la consulta y recuperación; descarga/construcción se registran aparte. La evaluación final necesita responsables de pertinencia y correspondencias fijadas previamente.

## Referencias de implementación

La autoridad académica es la sección 1.3.3.1 y bibliografía del Word proporcionado. Referencias técnicas: https://docs.python.org/3.12/library/ast.html ; https://lxml.de/xpathxslt.html ; https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.traversal.breadth_first_search.bfs_layers.html ; https://www.sqlite.org/fts5.html ; https://arxiv.org/abs/2104.08663 ; https://www.elastic.co/docs/reference/elasticsearch/rest-apis/search-rank-eval . No se modifica el documento de tesis.

## Estado después de implementar la versión 0.1.0

Actualizado el 14 de noviembre de 2026. La tabla inicial se conserva como planificación previa; esta sección describe el resultado real.

| ID | Estado actual | Evidencia o pendiente |
|---|---|---|
| R2-01 | Implementado | Paquete Python, python -m r2, entry point r2 y lanzador Windows; schema_version=1 |
| R2-02 | Implementado para fuentes locales | Git resuelve revisiones y lee blobs; snapshots generan hashes. Descarga automática y API GitHub pendientes |
| R2-03 | Integrado | Selector transitivo antes de leer contenido; colección identificada por política; consulta rechaza otro modo |
| R2-04 | Implementado con límites estáticos | AST, lxml/XPath, CSV/manifiesto, referencias explícitas y avisos; sin inferencia completa de tipos ni ejecución Odoo |
| R2-05 | Implementado | Bloques candidatos, revisiones y group_id para unificar evidencias como cambio semántico |
| R2-06 | Implementado | SQLite, inventario, show y exportación canónica JSON; construcción atómica sin sobrescritura |
| R2-07 | Implementado con límites | Claves Odoo y propiedades API; símbolos genéricos son candidatos, no resolución semántica completa |
| R2-08 | Implementado | NetworkX bfs_layers; alternativa explícita stdlib_bfs_fallback para host sin NetworkX; caminos estables |
| R2-09 | Implementado, pendiente calibración final | Filtros y orden determinista declarados; no se afinó contra casos reservados |
| R2-10 | Implementado | Texto/JSON en inglés, diez resultados, resumen completo y log JSONL opcional |
| R2-11 | Implementado | FTS5 BM25 sobre unidades y filtros compartidos; recorrido desactivado en la referencia |
| R2-12 | Implementado como evaluador | Fórmulas comprobadas con fixtures sintéticos. Juicios reales y evaluación final pendientes |
| R2-13 | Implementado | Pruebas integrales y demostración con código real del núcleo y módulo original |
| R2-14 | Implementado | README, manifiesto, anotaciones de desarrollo, ejemplos y lanzador local |
| R2-15 | Pendiente | Base completa 16–19, auditoría de fuentes, revisión independiente y muestra de treinta migraciones |
| R2-16 | Pendiente de laboratorio | No se ejecutó una nueva migración desde cero durante esta implementación; el ejemplo de R2 es consulta de lectura |

### Declaración efectiva de herramientas y métodos

Se utilizó Python 3.12, ast, lxml/XPath, Git local para el mecanismo de recolección, NetworkX en las pruebas iniciales Docker, SQLite/FTS5, argparse, JSON/JSONL, hashlib, difflib, csv, statistics y unittest. El flujo de demostración final en Windows utiliza BFS estándar porque NetworkX no está instalado en el runtime local; lo declara graph_implementation. La instalación estándar del paquete sí incluye NetworkX. No se instaló nada en el runtime administrado de Codex.

No se utilizó la API REST de GitHub. No se usaron pandas, scikit-learn ni statsmodels: las métricas explícitas se implementaron con Python estándar y JSON; pandas no es dependencia del núcleo. LibCST, upgrade-util, pylint-odoo, cloc, upgrade_code y odoo-module-migrator no se ejecutan dentro de R2. PostgreSQL y las instancias Odoo no son dependencias de consulta. Docker se utilizó como entorno Python de pruebas iniciales; la comprobación posterior usa el runtime local porque dos revisiones automáticas de permisos para Docker agotaron su plazo. No se conectó ningún modelo de lenguaje ni se implementó RAG generativo.

El análisis de contenido se operacionalizó como clasificación estructural, evidencia antes/después y anotaciones explícitas. BFS registra profundidad mínima y evita ciclos. El orden es determinista y versionado. La comparación léxica usa BM25. Los juicios de pertinencia son externos y explícitos. La ciencia del diseño orientó construir y verificar el prototipo, pero no se ha completado la evaluación académica. Los resultados sintéticos no se reportan como C1/P1/C2 reales de la tesis ni como superioridad sobre BM25.

## Ajuste metodológico 0.2 del 14 de noviembre de 2026

La autoridad de requisitos permanece en la tesis; este backlog no la redefine. El estado actual, con diferencias iniciales y evidencia de corrección, se registra en audit/TRAZABILIDAD.md y audit/INFORME_CUMPLIMIENTO.md. Las secciones previas de 0.1 son históricas.

Se implementaron cliente REST y capturas auditables, inventario para tres saltos, registro de asignación/exclusiones, manual de codificación, relación M:N evidencia/cambio e historial, revisión de vigencia, XML-ID cualificados, relaciones QWeb/seguridad, self.x resuelto o pendiente, todas las evidencias por arista, semillas explícitas, BM25 con lista blanca, evaluador con pandas/sklearn, medición separada y contrabalanceada y protocolo congelable. Python 3.12, NetworkX real, entorno aislado y reconstrucción limpia se verificaron de nuevo.

Pendientes: marco muestral completo, seis criterios revisados para candidatas, confirmación del corte y modelo, responsables/juicios independientes, calibración final solo con construcción, congelación efectiva, revisión del corpus y evaluación de treinta casos. Hay nueve unidades de fuente parciales y 52 entradas de una ventana mensual; no son un corpus completo ni treinta migraciones elegibles. statsmodels no se utiliza sin una inferencia justificada; la discrepancia de Tabla 4 queda documentada para decisión académica, fuera del Word.


## Integración 0.3 del componente final

Completado: componente final intacto en r2/adquisition; referencia y archivo anteriores separados; CLI con catálogo y borrado; ingestión de unidades aceptadas; conversión de diffs y PR; contexto documental; persistencia de artefactos en esquema 3; consulta offline y BM25; evaluación de ingeniería y cliente de metadatos independiente. Documentación y comandos actualizados.

Los contratos anteriores de capturas, interruptor y hashes dentro de adquisición son históricos. No se completaron mediante esta integración el catálogo real, el corpus académico, la revisión independiente ni las decisiones pendientes. La auditoría académica del corpus nuevo debe conectarse explícitamente antes de habilitar su evaluación final.
