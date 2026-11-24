# Experimentos R2

Este directorio conserva la evaluación de la base local y de la recuperación de información.

- `variants/`: configuración de adquisición, normalización, recorrido, filtros, ordenación y BM25.
- `logs/`: registros de adquisición y ejecución, revisiones de fuentes, comandos, errores y tiempos.
- `results/`: cobertura C1, precisión P1, cobertura C2, conformidad V1, tiempo T1 y comparación con BM25.

Las variantes deben usar la misma colección, revisiones, consultas, filtros, límite y juicios cuando se comparen. Las salidas vacías se conservan y se reportan; no se eliminan del cálculo de manera silenciosa. Cada artefacto debe identificar el MIG correspondiente.
