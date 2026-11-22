# Requisitos cumplidos: reporte y evaluación

## Propósito

Reporte, búsqueda, comparación con líneas base y evaluación pertenecen a
R2.2. R2.1 termina en el cruce inicial.

Presentar candidatos trazables y medir el motor relacional frente a una línea base léxica.

| ID | Requisito cumplido | Código principal |
|---|---|---|
| RP-01 | Filtrar por versión, capa y profundidad | `report.search_units` |
| RP-02 | Deduplicar hunks idénticos con IDs estables | `report.py` |
| RP-03 | Calcular conteos antes del límite | `summary` |
| RP-04 | Mostrar hasta diez hunks o secciones documentales por consulta | Parámetro `limit` |
| RP-05 | Conservar fuente, localizador, evidencia, camino y relaciones | Contrato del reporte |
| RP-06 | Generar TXT y JSON | `render_report` y escritores |
| RP-07 | Validar conteos y caminos | `validate_report` |
| RP-08 | Ofrecer el control BM25 por unidades en la CLI | `engine=bm25`, FTS5 |
| RP-09 | Evaluar C1, P1, C2, V1 y T1 | `evaluation.normalized.evaluate` |
| RP-10 | Usar `null` cuando una métrica no es evaluable | Evaluador y validación |

**Entrada:** colección, addon, intervalo, capa, profundidad, límite y motor.  
**Salida:** reporte TXT/JSON y evaluación JSON cuando existe especificación revisada.

**Límites:** los resultados requieren revisión técnica; las métricas necesitan juicios independientes. El dashboard no está implementado.

**Pruebas:** `test_normalized_workflow.py`, `test_r2.py`, `test_caja_negra.py`, `test_oca_functionality.py` y metodología.

## Comparación del experimento de AWS

Graph y BM25 consultan el mismo corpus con el mismo addon, salto y límite.
El dossier conserva recomendaciones, colección, código y parches MIG/FIX.
La revisión asistida por IA registra capa, componente, motivos e incertidumbre.
La importación valida IDs, integridad, salto y completitud antes de calcular
C1, C2 y P1. Las secciones documentales de destino pueden cubrir una corrección
si explican el cambio aplicable al salto. Las estadísticas de grafo describen
coincidencias, atributos y aristas. Los juicios establecen pertinencia.

El lote conserva una selección de hasta diez URL públicas distintas por caso
y motor para revisión operativa. La evaluación usa unidades por consulta y
reporta la media pareada de P1 en la muestra congelada de treinta MIG. Los
parches de referencia quedan en el dossier. Los tiempos por etapa y por
consulta completa se registran con sus límites de medición.
[Procedimiento en AWS](../../../../aws-lab/EVALUACION_FINAL.md).
