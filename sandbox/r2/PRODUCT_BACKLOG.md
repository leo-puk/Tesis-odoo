# Product backlog de R2

## Objetivo

Entregar a un partner evidencia trazable de cambios de Odoo potencialmente relacionados con sus addons antes de migrarlos, reduciendo búsqueda manual sin reemplazar la revisión técnica.

## Backlog vigente

| ID | Componente | Capacidad | Criterio de aceptación | Estado |
|---|---|---|---|---|
| R2-001 | Adquisición | Capturar fuentes revisadas completas | Plan/catálogo validados; originales, inventario y estados conservados | Cumplido |
| R2-002 | Adquisición | Continuar ante red o codificación fallida | El error se registra y continúa el lote | Cumplido |
| R2-003 | Planner | Generar fuentes desde el addon | Dependencias, URL y avisos quedan en `planning.json` | Cumplido |
| R2-004 | Normalización | Crear unidades verificables | Fuente, localizador, capa, versión, entidades y advertencias | Cumplido |
| R2-005 | Persistencia | Reutilizar una colección | SQLite esquema 4 guarda unidades, entidades y términos | Cumplido |
| R2-006 | Cruce | Hallar identidades del addon en evidencia | Matches exactos incluyen ambas ubicaciones | Cumplido |
| R2-007 | Relaciones | Ampliar matches a cambios relacionados | Recorrido reproducible de 0 a 3 saltos | Cumplido |
| R2-008 | Reporte | Presentar candidatos trazables | TXT/JSON, máximo configurable y conteos totales | Cumplido |
| R2-009 | Consulta | Cambiar filtros sin recapturar | `query` reutiliza SQLite | Cumplido |
| R2-010 | Baseline | Comparar con búsqueda léxica | BM25 usa el mismo corpus y filtros | Cumplido |
| R2-011 | Evaluación | Medir C1/P1/C2/V1/T1 | Solo usa referencias y juicios explícitos | Cumplido técnicamente |
| R2-012 | R2.2 | Elegir addons fácilmente | `start` muestra addons y acepta números/rangos/nombres | Cumplido |
| R2-013 | R2.2 | Usar versiones locales | Diff por SHA local sin compare web | Cumplido |
| R2-014 | R2.2 | Analizar varios addons | Una colección genera reporte por addon | Cumplido |
| R2-015 | Configuración | No repetir rutas | Configuración reutilizable fuera del repo | Cumplido |
| R2-016 | Calidad | Detectar regresiones | Suite de caja negra, blanca e integración | Cumplido |
| R2-017 | UX | Incorporar interfaz gráfica | Selector de carpetas, versiones, addons y resultados | Pendiente |
| R2-018 | Insights | Mostrar dashboard | Gráficos enlazan capas, profundidad y evidencia | Pendiente |
| R2-019 | Git | Asistir ramas faltantes | Explica y confirma antes de `git fetch` | Pendiente |
| R2-020 | Cobertura | Añadir fuentes específicas por salto | PR, commits y diffs revisados complementan el diff global | Pendiente prioritario |
| R2-021 | Rendimiento | Procesar diffs grandes | Análisis estático previo genera un diff filtrado y registra su alcance | Cumplido técnicamente |
| R2-022 | Filtros | Medir pérdida por filtros | Reporta candidatos antes/después, recall y exclusiones | Pendiente prioritario |
| R2-023 | Relaciones | Medir aporte por profundidad | Relevantes nuevos, ruido y caminos perdidos por nivel | Pendiente prioritario |
| R2-024 | Tesis | Validar con verdad independiente | Muestra congelada, revisores y juicios reproducibles | Pendiente |
| R2-025 | Versiones | Tratar saltos múltiples por separado | Cada salto conserva fuentes y bindings propios | Parcial |
| R2-026 | Distribución | Instalar como producto | Paquete versionado probado en Windows y Linux | Pendiente |

## Prioridad siguiente

1. R2-020: aumentar evidencia específica del intervalo.
2. R2-022 y R2-023: medir filtros y relaciones.
3. R2-018: presentar insights sin perder trazabilidad.
4. R2-024: cerrar la evaluación académica independiente.

## Definición de terminado

Una capacidad termina cuando su contrato público está documentado, tiene pruebas proporcionales al riesgo, conserva trazabilidad, no modifica el addon y pasa la suite integral. Una demo sintética no sustituye la validación académica.
