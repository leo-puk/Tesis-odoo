# Requisitos cumplidos: normalización y persistencia

## Propósito

Convertir artefactos aceptados en unidades verificables y almacenarlas en una colección reproducible.

| ID | Requisito cumplido | Código principal |
|---|---|---|
| NP-01 | Leer solo unidades aceptadas y conservar omitidas con motivo | `readers.read_session` |
| NP-02 | Decodificar sin sustituir silenciosamente bytes inválidos | `decoding.py` |
| NP-03 | Parsear diff, Python, XML, CSV, manifiesto, texto, Markdown, HTML y PR soportados | `parsers.py`, `diff.py`, `units.py` |
| NP-04 | Crear unidades con versión, capa, entidades, términos, localizador y advertencias | `convert_units` |
| NP-05 | Validar releyendo el artefacto retenido | `schema.validate_collection` |
| NP-06 | Prohibir relaciones precalculadas en unidades | `schema.py` |
| NP-07 | Calcular IDs y revisión deterministas | `records.fingerprint` y pipeline |
| NP-08 | Persistir esquema 4 `normalized-units`, separando atributos de grafo y contenido recuperable | `storage.build_normalized`, `records.split_unit` |
| NP-09 | Indexar entidades y términos FTS5/BM25 | `unit_entities`, `unit_terms`, `unit_search` |
| NP-10 | No sobrescribir colecciones | `build_normalized` |

**Entrada:** `inventory.json` y bindings opcionales.  
**Salida:** `collection.sqlite` con sources, artifacts, information_units sin texto duplicado, unit_content e índices.

**Límites:** valida fidelidad contra la captura, no autenticidad remota. Sintaxis parcial produce advertencias; unidades sin intervalo completo no son cambios finales.

**Pruebas:** `test_normalization.py`, `test_normalization_fidelity.py`, `test_normalization_scopes.py`, `test_normalization_imports.py` y `test_session_integration.py`.
