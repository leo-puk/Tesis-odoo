# Requisitos cumplidos: reporte y evaluación

## Propósito

Presentar candidatos trazables y medir el motor relacional frente a una línea base léxica.

| ID | Requisito cumplido | Código principal |
|---|---|---|
| RP-01 | Filtrar por versión, capa y profundidad | `report.search_units` |
| RP-02 | Deduplicar hunks idénticos con IDs estables | `report.py` |
| RP-03 | Calcular conteos antes del límite | `summary` |
| RP-04 | Mostrar entre 1 y 10 resultados | Parámetro `limit` |
| RP-05 | Conservar fuente, localizador, evidencia, camino y relaciones | Contrato del reporte |
| RP-06 | Generar TXT y JSON | `render_report` y escritores |
| RP-07 | Validar conteos y caminos | `validate_report` |
| RP-08 | Ofrecer BM25 sobre las mismas unidades | `engine=bm25`, FTS5 |
| RP-09 | Evaluar C1, P1, C2, V1 y T1 | `evaluation.normalized.evaluate` |
| RP-10 | Usar `null` cuando una métrica no es evaluable | Evaluador y validación |

**Entrada:** colección, addon, intervalo, capa, profundidad, límite y motor.  
**Salida:** reporte TXT/JSON y evaluación JSON cuando existe especificación revisada.

**Límites:** los resultados requieren revisión técnica; las métricas necesitan juicios independientes. El dashboard no está implementado.

**Pruebas:** `test_normalized_workflow.py`, `test_r2.py`, `test_caja_negra.py`, `test_oca_functionality.py` y metodología.
