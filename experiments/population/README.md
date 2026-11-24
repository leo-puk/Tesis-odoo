# Población experimental

Este directorio contiene los treinta casos MIG de la muestra. Cada `migN` tiene:

- `config.json`: identidad, procedencia, salto de versión, revisiones y estado de preparación del caso.
- `results/results.json`: resultados de R1, R2, R3 y R4 para ese caso, junto con artefactos y limitaciones.

Los archivos iniciales usan `not_configured` y `not_run`. Esos valores son estados explícitos, no resultados. Deben sustituirse únicamente con evidencia de una ejecución registrada. No se deben cambiar etiquetas, muestras o configuraciones de la evaluación final después de observar sus resultados.
