# Product backlog de R2

## Objetivo

La atribución funcional vigente sitúa planificación, adquisición,
normalización, persistencia y cruce inicial en R2.1. Desde la extracción de
relaciones, búsqueda y ordenación hasta reporte, CLI y evaluación corresponde
a R2.2. Los comandos pueden coordinar ambos resultados.

Entregar a un partner evidencia trazable de cambios de Odoo potencialmente relacionados con sus addons antes de migrarlos, reduciendo búsqueda manual sin reemplazar la revisión técnica.

## Backlog vigente

| ID | Componente | Capacidad | Criterio de aceptación | Estado |
|---|---|---|---|---|
| R2-001 | R2.1 Adquisición | Capturar fuentes revisadas completas | Plan/catálogo validados; originales, inventario y estados conservados | Cumplido |
| R2-002 | R2.1 Adquisición | Continuar ante red o codificación fallida | El error se registra y continúa el lote | Cumplido |
| R2-003 | R2.1 Planner | Generar fuentes desde el addon | Dependencias, URL y avisos quedan en `planning.json` | Cumplido |
| R2-004 | R2.1 Normalización | Crear unidades verificables | Fuente, localizador, capa, versión, entidades y advertencias | Cumplido |
| R2-005 | R2.1 Persistencia | Reutilizar una colección | SQLite esquema 4 guarda unidades, entidades y términos | Cumplido |
| R2-006 | R2.1 Cruce | Hallar identidades del addon en evidencia | Matches exactos incluyen ambas ubicaciones | Cumplido |
| R2-007 | R2.2 Relaciones | Ampliar matches a cambios relacionados | Recorrido reproducible de 0 a 3 saltos | Cumplido |
| R2-008 | R2.2 Reporte | Presentar candidatos trazables | Hunks y documentación por consulta, estadísticas y hasta diez URL por caso y motor en el lote | Cumplido técnicamente |
| R2-009 | R2.2 Consulta | Cambiar filtros sin recapturar | `query` reutiliza SQLite | Cumplido |
| R2-010 | R2.2 Baseline | Comparar con búsqueda léxica | Graph frente a BM25 por unidades en CLI y experimento; mismo corpus, consultas y límite | Cumplido técnicamente |
| R2-011 | Evaluación | Medir C1/P1/C2/V1/T1 | Solo usa referencias y juicios explícitos | Cumplido técnicamente |
| R2-012 | R2.2 | Elegir addons fácilmente | `start` muestra addons y acepta números/rangos/nombres | Cumplido |
| R2-013 | R2.1 | Preparar evidencia con versiones locales | Diff por SHA local filtrado antes de normalización y cruce | Cumplido |
| R2-014 | R2.1 y R2.2 | Analizar varios addons | R2.1 crea colección y cruces; R2.2 produce relaciones y reporte por addon | Cumplido |
| R2-015 | Configuración | No repetir rutas | Configuración reutilizable fuera del repo | Cumplido |
| R2-016 | Calidad | Detectar regresiones | Suite de caja negra, blanca e integración | Cumplido |
| R2-017 | UX | Incorporar interfaz gráfica | Selector de carpetas, versiones, addons y resultados | Pendiente |
| R2-018 | Insights | Mostrar dashboard | Gráficos enlazan capas, profundidad y evidencia | Pendiente |
| R2-019 | Git | Asistir ramas faltantes | Explica y confirma antes de `git fetch` | Pendiente |
| R2-020 | R2.1 Adquisición | Complementar el diff filtrado con fuentes por salto | Diffs OCA auxiliares por dependencias, documentación y capturas integradas con procedencia | Cumplido técnicamente |
| R2-021 | Rendimiento | Procesar diffs grandes | Análisis estático previo genera un diff filtrado y registra su alcance | Cumplido técnicamente |
| R2-022 | Filtros | Medir pérdida por filtros | Reporta candidatos antes/después, recall y exclusiones | Pendiente prioritario |
| R2-023 | Relaciones | Medir aporte por profundidad | Relevantes nuevos, ruido y caminos perdidos por nivel | Pendiente prioritario |
| R2-024 | Tesis | Ejecutar y documentar la validación | Dossier MIG/FIX, capa y componente en juicios, muestra congelada y P1 pareada | Flujo implementado. Ejecución y revisión de la muestra real pendientes |
| R2-025 | Versiones | Tratar saltos múltiples por separado | Cada salto conserva fuentes y bindings propios | Parcial |
| R2-026 | Distribución | Instalar como producto | Paquete versionado probado en Windows y Linux | Pendiente |

## Prioridad siguiente

1. Ejecutar y documentar la muestra de R2-024.
2. Medir el efecto de filtros y relaciones en R2-022 y R2-023.
3. Incorporar el dashboard de R2-018.

## Definición de terminado

Una capacidad termina cuando su contrato público está documentado, tiene pruebas proporcionales al riesgo, conserva trazabilidad, no modifica el addon y pasa la suite integral. Una demo sintética no sustituye la validación académica.
