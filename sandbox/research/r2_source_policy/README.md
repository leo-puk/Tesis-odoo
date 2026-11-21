# Selector de fuentes para R2

Selector independiente de fuentes para R2.1. La implementación integrada
actual incorpora adquisición, normalización, persistencia y cruce inicial en
R2.1; extracción de relaciones, búsqueda, reporte y evaluación pertenecen a
R2.2. Este selector conserva su contrato de procedencia y exclusión.

Desde sandbox, utilizando el contenedor de control:

```powershell
docker exec -w /workspace/research/r2_source_policy sbx-control python source_policy.py manifest.json --no-include-oca-migrations
docker exec -w /workspace/research/r2_source_policy sbx-control python source_policy.py manifest.json --include-oca-migrations
```

manifest.json debe existir en ese directorio. Es un array de registros con id único, kind, split y parent_ids explícitos. Puede contener metadatos y contenido adicionales. La salida entrega el contenido completo únicamente para accepted; excluded contiene solo ID y motivo.

Kinds: official_code, official_documentation, oca_guidance, openupgrade_analysis, oca_migration, oca_fix, derived. Splits: construction, evaluation_reference. Un derived necesita padres. Una fuente aparentemente general que se derive de una solución excluida también debe declarar ese origen.

El modo predeterminado excluye oca_migration, oca_fix y descendientes. El modo activado permite únicamente los de construcción. evaluation_reference y sus descendientes quedan excluidos en ambos modos. Los errores de procedencia abortan la selección. Los títulos MIG/FIX no se usan para decidir automáticamente el tipo de fuente.

Esta selección depende de la corrección del inventario de procedencia. No detecta contenido contaminado mal etiquetado. Debe ejecutarse antes de alimentar índices, grafos, resúmenes o modelos. Cada modo tendrá una colección y cachés independientes; no se reutiliza una colección construida con soluciones excluidas cambiando simplemente el flag.

Comprobación realizada: python -m unittest -v test_source_policy.py; seis pruebas correctas.
