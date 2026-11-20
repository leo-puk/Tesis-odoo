# Requisitos cumplidos: cruce

## Propósito

Comparar identidades técnicas del addon con el índice normalizado sin ejecutar código ni depender de palabras compartidas.

| ID | Requisito cumplido | Código principal |
|---|---|---|
| CR-01 | Leer Python, XML, CSV y manifiestos soportados | `crossing.code.read_code` |
| CR-02 | No importar ni ejecutar el código | Lectura AST, literal y XML estática |
| CR-03 | Conservar nombre, tipo, propietario y ubicación | Observaciones de `crossing.code` |
| CR-04 | Usar `unit_entity_lookup`, no escanear todo el texto | `engine.cross_module` |
| CR-05 | Exigir coincidencia tipada compatible | `crossing.rules` |
| CR-06 | Separar ausencia limpia, errores y análisis parcial | Estado, errores y unresolved |
| CR-07 | Evitar matches por comentarios y homónimos | Claves y filtros tipados |
| CR-08 | Entregar IDs y evidencia puntual a relaciones | Contrato ID-only |
| CR-09 | Persistir de forma reproducible sin sobrescribir | `save_result` |

**Entrada:** addon y `collection.sqlite`.  
**Salida:** `crossing.json` con semillas, ubicaciones, coincidencias y errores.

**Límites:** referencias dinámicas pueden quedar sin resolver. Una coincidencia indica relación potencial, no aplicabilidad final.

**Pruebas:** `test_crossing.py`, `test_crossing_corrections.py`, `test_partial_anchors.py` e integraciones.
