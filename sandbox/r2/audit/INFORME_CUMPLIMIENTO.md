> Informe de la entrega 0.2. La integración posterior del componente final está documentada en [INTEGRACION_030.md](INTEGRACION_030.md); sus contratos sustituyen los de adquisición descritos aquí.

# Informe de cumplimiento R2 0.2

14 de noviembre de 2026. Este informe distingue corrección de software, evidencia de funcionamiento y validación académica pendiente. No declara cumplimiento total ni modifica la tesis.

## Identificación y protección de archivos

Base Git registrada antes de editar: 9ee4dbd9f2279c3f45620d6691131a39c4db608a. R2 era no seguido y había cambios ajenos en el repositorio; no se revirtieron ni se incorporaron a un commit. No hay un nuevo commit de entrega. initial-state.json y final-state.json identifican el contenido mediante hashes, además de la base Git.

Revisión de código actual (hash del conjunto de módulos): 3674c96f890aab33e0b7771758086e2e4c303f81525036394b57cd089e276b91. La revisión previa de esta entrega fue 1bcfec5213e30d0979e9f27cd71a2d8fc87290bcc1a621dd564aca6621dff71c; la continuación añade diagnóstico HTTP y fichas de selección. Revisión de colección, sin cambios: f649243c090c3de899c6d849605400468923d80146d243615297f57d34a29c4d. Los archivos individuales y dependencias tienen hashes/versión en final-state.json y requirements-lock.txt.

El SHA256 inicial y final del Word coincide: 317B8F1E37EE0D8A63181451C7205D43B06C4412B8A48A8A5414FD4831898D57. No se editó, regeneró ni ejecutó ningún script que lo modificara. Los scripts de edición del material histórico externo no se ejecutaron.

## Corregido y verificado

- Python 3.12.14, entorno aislado del proyecto y segundo entorno limpio. Dependencias fijadas, instalación editable local, Git 2.54.0.windows.1, SQLite FTS5 3.53.1 y llamada real a networkx.bfs_layers.
- La continuación eleva la suite a 33 pruebas por las fichas de revisión. Se conserva la separación de ejecuciones con NetworkX real, compatibilidad y entorno limpio en tests-networkx.txt, tests-compatibility.txt y tests-clean-environment.txt. Son los mismos casos bajo tres condiciones; no se suman como requisitos diferentes ni como evidencia de precisión académica. La comprobación anterior de dependencias no encontró incompatibilidades.
- Importación Git desde un repositorio temporal real, dos commits fijos y lectura de blobs. La prueba detectó y permitió corregir un pathspec vacío que impedía importar el repositorio completo.
- Normalización de XML-ID por módulo, declaraciones/referencias separadas, resolución estática de self.x y preservación de unresolved; QWeb t-call/herencia y referencias de grupos/datos/seguridad.
- Conservación de todas las evidencias de cada arista; BFS mínimo multiorigen, ciclos y desempates reproducibles. La prueba de camino indirecto conserva dos archivos de evidencia sobre una misma arista.
- Modelo explícito de fuentes/comparaciones/evidencias/cambios y enlace M:N. Revisión con responsable, fecha, categoría, condiciones y vigencia del salto; historial y agrupación.
- BM25 con lista blanca de contenido, no JSON administrativo; filtros/estado/límite compartidos. El orden y semillas son explícitos y congelables, no calibrados con la evaluación.
- Correcciones del evaluador: estado/límite/profundidad explícitos, correspondencias de salto/elemento, vigencia y condiciones para C1, vacíos/N/A y unión por módulo, hallazgos válidos fuera del MIG separados, mediciones contrabalanceadas y datos individuales.
- pandas ejecutado para agregaciones/exportaciones y scikit-learn ejecutado para los cocientes exactos de P1 y C2 sobre sus respectivas unidades. La exportación CSV se ejercitó en pruebas y también sobre el inventario real de fuentes.
- V1 estructural ampliado, con revisión lingüística y pertinencia/autenticidad humana separadas. output-conformity.json no se presenta como V1 académico completo.

## Implementado pendiente de evaluación

La API REST fue ejecutada con una búsqueda del piloto y con tres ventanas mensuales; se archivaron metadatos de PR, revisiones, autor, fechas, fusión, rama/SHA y archivos, sin cuerpos ni parches. Hay paginación, protección de tokens, errores y rechazo de búsquedas incompletas o mayores de 1000. Eso no acredita la población completa de 1.3.4.

La captura documental incluye nueve unidades (tres comparaciones parciales de núcleo, tres de changelog y tres de guías) para 16→17, 17→18 y 18→19. Conserva bytes, extracción y hashes distintos. La primera captura detectó el traslado de fields.py en 19; el suplemento usa la ruta real orm/fields.py y declara que faltan los otros archivos del reparto. No se afirmó identidad de rutas ni corpus completo.

La colección tiene 9 fuentes/comparaciones, 432 fragmentos candidatos, 36 263 ocurrencias de elementos y 31 715 ocurrencias de relaciones. No son 432 incompatibilidades verificadas ni 31 715 aristas semánticas únicas. No tiene cambios revisados independientemente. La demostración separada tiene dos revisiones del desarrollador sobre el piloto, que está excluido de evaluación.

La reconstrucción offline se ejecutó y produjo la misma revisión de colección; reconstruction-check.txt registra la igualdad. La colección general sigue pendiente de codificación y auditoría de pertinencia. Las licencias no verificadas y las limitaciones de captura constan en el inventario; no se inventaron commits upstream.

El interruptor de fuentes excluye MIG/FIX y derivados declarados, y las referencias reservadas se excluyen antes de leer contenido. Un registro adicional exige evidencia de asignación, corte/criterios para migraciones de construcción e identidad de fuentes generales; la etiqueta construction sola no basta en modo auditado. Se excluyen conservadoramente once módulos presentes en el laboratorio histórico, incluido sale_advance_payment; historical-exclusions.json conserva los motivos y hashes de metadatos. No se afirma descubrir copias ocultas o procedencia falsificada.

## Pendiente por datos o revisión humana

- El marco capturado es parcial: octubre de 2026, 3 entradas hacia 17, 11 hacia 18 y 38 hacia 19 (52 en total). partial-frame-summary.json lo declara incompleto.
- Falta confirmar modelo y corte temporal; el de agosto de 2025 continúa como referencia ilustrativa, no como decisión final adoptada.
- Faltan los seis criterios revisados y evidencia de mantenedor independiente, manifiestos, pruebas, dependencias instalables y ausencia de FIX de comportamiento para candidatas elegibles. No se interpretó MEMBER/APPROVED automáticamente como mantenedor acreditado.
- sample conserva orden y semilla y bloquea el primer caso sin revisar en cada estrato. selection-status.json registra casos, criterios faltantes y cero seleccionados definitivos; no inventa treinta elegibles.
- Faltan responsables reales, correspondencias y juicios independientes, revisión lingüística de salida y condiciones definitivas de caché. freeze se niega a crear un protocolo oficial sin esos datos.
- La precisión/cobertura reales, meta C1 ≥ 90 % y comparación con BM25 no se han medido. Los valores de fixtures son pruebas del software y no resultados de tesis.

## Discrepancias que requieren decisión académica

1. Tabla 4 menciona statsmodels para actividades de R2, pero 1.3.3.1 no especifica una inferencia que lo requiera. No se aplicó McNemar/Wilson ni otra llamada decorativa. Está instalado en el entorno de auditoría, pero no se cuenta como método usado. Debe resolverse la discrepancia de asignación sin editar el Word en este trabajo.
2. Debe ratificarse el límite operacional T1: se ofrecen recuperación interna, hasta validación/serialización y CLI hasta completar stdout, separados. El evaluador utiliza el segundo y conserva medidas individuales y orden; el tercero está en un log independiente.
3. Deben ratificarse agregación P1 macro, reglas/semillas/profundidad y tratamiento documental exacto del corpus general posterior al corte frente a las migraciones de construcción anteriores. Se preparan como parámetros congelables, no como decisiones atribuidas unilateralmente a la tesis.

## Índice de entrega

1. Código: ../r2; base Git y contenido: initial-state.json/final-state.json.
2. Matriz: TRAZABILIDAD.md, con estado inicial y cierre técnico por requisito.
3. Fuentes activas: corpus-normalized-v2/inventory.json; asignaciones: assignments.json; exclusiones históricas y selección en esta carpeta.
4. Manual: ../docs/MANUAL_CODIFICACION.md.
5. Protocolo: ../docs/PROTOCOLO_EVALUACION.md y protocol-template.json.
6. Pruebas y entornos: tests-*.txt y environment*.json.
7. Reproducción: ../docs/REPRODUCCION.md y ../requirements-lock.txt.
8. Este informe distingue correcciones, preparación y bloqueos académicos.

El piloto histórico continúa siendo una ejecución con código adaptado y pruebas en otra base. No fue reescrito como migración autónoma, no acredita equivalencia y sus tiempos no se usaron como T1.

## Continuación de preparación de expedientes

La utilidad audit/prepare_review_packets.py prepara fichas sin leer soluciones ni modificar el índice. El intento de ampliar metadatos recibió HTTP 403 en la primera candidata; se archivó el bloqueo y se suspendieron las solicitudes siguientes. review-packets/README.md explica la reanudación y summary.json distingue las tres fichas pendientes. Ningún criterio se aprobó ni se inventó un responsable. Modelo/corte y responsables siguen pendientes de información del usuario.

El usuario confirmó expresamente que modelo/snapshot, corte documentado y responsables todavía no están definidos. pending-academic-decisions.json registra esta respuesta. No se adopta el corte ilustrativo como definitivo ni se congela la evaluación; la preparación del corpus y de instrumentos puede continuar.
