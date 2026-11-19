# Protocolo congelable de evaluación R2

## Actualización de integración 0.3

El cliente de selección está en `r2/evaluation_sources`; adquisición final se destina a construcción y puede conservar PR completos. No se usan esos PR completos para preparar expedientes reservados. Los controles académicos siguen fuera de adquisición. Una unidad accepted no acredita auditoría académica; el constructor de sesiones mantiene assignment_audited=false hasta incorporar una auditoría independiente explícita. El fingerprint de código incluye recursivamente los subpaquetes: no reutilizar protocolos antiguos como si identificaran esta entrega. El nuevo contrato y sus límites están en [Integración](INTEGRACION_ADQUISITION.md).

Autoridad: Tabla 3 y 1.3.3.1/1.3.4. Este archivo define el procedimiento y las decisiones operacionales que deben revisarse y fijarse antes de medir. No constituye una evaluación ejecutada ni inventa responsables. El estado actual está en audit/selection-status.json y audit/INFORME_CUMPLIMIENTO.md.

## Independencia y muestra

El cliente GitHub captura consulta, fechas, PR/autor, fusión, rama, SHA, revisiones y lista de archivos sin cuerpos ni parches de soluciones. La aprobación de un usuario diferente no demuestra que sea mantenedor: se necesita evidencia de identidad. La lista de archivos no prueba por sí sola que todo el PR migra un único módulo, que sus dependencias sean instalables ni que no existan correcciones de comportamiento. Los seis criterios se registran como pass/fail/pending con evidencia y responsable.

El corte de 2025-08-01 se conserva solo como referencia ilustrativa de la tesis. Falta fijar el modelo y confirmar el corte definitivo. La construcción de información general de 19.0 con fuentes posteriores y la restricción temporal de migraciones de construcción son asuntos distintos; la política académica precisa sobre sus revisiones debe confirmarse antes de evaluar.

Se fija semilla, orden por número de PR (desempate repositorio para obtener orden total), tres estratos y diez casos por estrato. sample registra la permutación, descartes y reemplazos; se detiene ante el primer candidato sin revisar de un estrato, en vez de saltarlo y sesgar la muestra. Excluye sale_advance_payment y cualquier caso señalado como usado en desarrollo. Debe completarse el registro de otros casos históricos inspeccionados antes de fijar la selección final; su ausencia no se interpreta como independencia demostrada.

La selección no está completa. El JSON contiene 52 entradas reales de una ventana mensual, con criterios pendientes. No se fabrican treinta casos elegibles. Las capturas del piloto y de la ventana prueban el cliente, no la exhaustividad de una población.

## Congelación

Antes de medir se fijan colección, fuentes y exclusiones, selección completa, consultas y contenido de módulos originales, relaciones, semillas, ranking, profundidad, límite, estado verified, campos BM25, agregación P1, responsable real de juicios, repeticiones y caché. El comando freeze genera un fingerprint de parámetros, código, colección, consultas y selección. Rechaza falta de responsables o de una selección auditada de treinta casos. La evaluación académica exige NetworkX real y asignación de fuentes auditada, no el modo de compatibilidad.

La configuración propuesta, pendiente de aprobación académica, usa P1 macro sobre consultas no vacías; informa cuántas quedan no definidas. No se aplica a P1/C2 la meta de C1. Los parámetros de ranking y profundidades solo se ajustan con construcción. Tras congelar no se incorporan juicios ni soluciones al índice.

## Unidades y juicios

C1 se calcula sobre cambios de referencia evaluables, con cubierta toda la información disponible en la base, no solo el top diez. Cada correspondencia debe citar cambio verified existente, evidencia, salto correcto y elemento afectado. Formato/administración ajenos a migración se separan del denominador. C1 se desglosa por módulo y salto.

P1 usa entradas pertinentes y aplicables / entradas entregadas. sklearn.precision_score se aplica con una etiqueta verdadera por entrada correctamente juzgada y todas las entradas como recuperadas: representa exactamente ese cociente. Se protege antes el caso vacío (None). No se entrena un clasificador.

C2 usa cambios de referencia pertinentes explicados por la primera vista / cambios pertinentes. sklearn.recall_score se aplica a una etiqueta positiva por cambio de referencia y a su pertenencia a la unión cubierta. Sin referencias es None; con referencias y salida vacía es cero. Se agregan consultas por módulo mediante conjuntos de IDs, sin sumar repetidamente un mismo cambio.

Cada juicio incluye relevant, applicable y justification. Los hallazgos válidos sin correspondencia en el MIG se reportan aparte. No se asigna irrelevancia a un resultado sin juzgar: se bloquea la medición y se informa su ID. Los juicios están en un JSON externo y nunca se incorporan al índice. El modo --development se etiqueta development_only=true y se utiliza únicamente para comprobaciones de ingeniería.

Pandas organiza resultados, agrega por motor/módulo/salto y exporta queries.csv, coverage.csv, coverage-by-module-jump.csv y measurements.csv. Las fórmulas se verifican con casos sintéticos, que no se reportan como evidencia empírica.

## V1 y T1

V1 automático comprueba claves, límites, duplicados, capas/estados, contadores, salto, rango de profundidad, extremos y evidencias de cada arista en la versión de origen, revisiones y condiciones de verified. No acredita el inglés de textos libres, autenticidad upstream ni pertinencia por la presencia de claves. La revisión lingüística se registra por separado; V1 queda no determinado si falta esa revisión. BM25 conserva fuentes y bloques pero no finge profundidad o camino estructural.

Se registran tres límites temporales diferentes:

1. internal_seconds: análisis del módulo y recuperación hasta formar la estructura de primera vista/resumen.
2. until_validated_serialized_view_seconds: añade validación y primera serialización de JSON y texto. Es el límite operacional propuesto de T1 para comparación del evaluador; no incluye transmisión/representación del terminal.
3. cli_until_stdout_completed_seconds: medido por la CLI desde su entrada, incluye parseo y escritura/flush en stdout; se conserva en --timing-log separado porque no puede conocerse antes de terminar de escribir la misma respuesta.

La descarga/extracción de fuentes y construcción se miden aparte, con límites descritos en los reportes de captura y build. El evaluador alterna el orden de motores por consulta y repetición. Conserva cada medida, posición, versiones, equipo, colección y parámetros. Cache_state=uncontrolled no se presenta como caché fría. El procedimiento definitivo de caché debe fijarse antes de la evaluación final. No se convierten estos tiempos en horas ahorradas por un partner.

## Discrepancias de herramientas

Tabla 4 asigna pandas/scikit-learn/statsmodels al análisis; las dos primeras se utilizan de forma efectiva como se indica arriba. 1.3.3.1 no exige contrastes inferenciales específicos de statsmodels, y Tabla 4 especifica McNemar e intervalos para R1. R2 no aplica McNemar/Wilson por obligación de usar una biblioteca. Su uso literal en R2 queda como discrepancia de Tabla 4 pendiente de decisión académica, fuera del Word. Que statsmodels esté instalado en el entorno de auditoría no se cuenta como método utilizado.
