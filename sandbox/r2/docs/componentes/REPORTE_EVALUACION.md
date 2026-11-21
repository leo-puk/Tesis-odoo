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
| RP-04 | Mostrar entre 1 y 10 resultados | Parámetro `limit` |
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

El experimento compara exclusivamente Graph y BM25 por unidades sobre el
mismo corpus, entrada y límite de diez resultados. La comparación histórica
por fuentes completas queda fuera del protocolo acordado. El dossier conserva
recomendaciones, contenido de la colección, código del addon y parches MIG
para emitir juicios asistidos por IA con motivo e incertidumbre. Su importación
valida IDs, integridad, salto y completitud antes de calcular las métricas.
El procedimiento incremental está en `aws-lab/EVALUACION_FINAL.md`.

Los MIG se revisan como referencia externa para identificar correcciones
manuales evaluables. Sus parches quedan fuera de los inventarios de entrada
del experimento. La existencia de una coincidencia técnica requiere revisión
para establecer su utilidad. Los tiempos por etapa y por consulta completa
se registran con sus límites de medición.
