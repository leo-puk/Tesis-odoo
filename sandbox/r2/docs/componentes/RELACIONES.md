# Requisitos cumplidos: relaciones

## Propósito

Expandir coincidencias directas hacia unidades conectadas mediante identidades técnicas verificables.

| ID | Requisito cumplido | Código principal |
|---|---|---|
| RE-01 | Validar esquema, revisión, reglas e índices | `relations.engine.execute_query` |
| RE-02 | Relacionar por identidad completa y tipo aprobado | `extraction.py`, `rules.py` |
| RE-03 | Excluir palabras, versiones, capas y menciones genéricas | Familias y reglas negativas |
| RE-04 | Conservar evidencia localizada en ambos extremos | Serialización de aristas |
| RE-05 | Recorrer desde múltiples semillas con distancia mínima | `traversal.py` |
| RE-06 | Limitar profundidad a 0–3 | API y CLI |
| RE-07 | Conservar ciclos, conexiones laterales y caminos verificables | Grafo de consulta |
| RE-08 | Validar resultados recargados contra SQLite | Replay y validadores |
| RE-09 | Persistir sin alterar colección ni cruce | `save_graph` |

**Entrada:** cruce, colección y profundidad.  
**Salida:** `relations.json` con vecindario, distancias, caminos y evidencia.

**Límites:** el grafo es técnico y no dirigido; no afirma causalidad. Más profundidad puede añadir cobertura y ruido.

**Pruebas:** `test_relation_extraction.py`, `test_relation_traversal.py` y `test_relation_extraction_integration.py`.
