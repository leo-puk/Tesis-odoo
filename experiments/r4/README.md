# Experimentos R4

Este directorio conserva la evaluación del detector y de la migración multicapa.

- `variants/`: reglas, configuración fija del modelo, saltos y líneas base comparadas.
- `logs/`: detección, transformaciones, solicitudes y respuestas del modelo, instalación, pruebas y verificación R3.
- `results/`: precisión y cobertura de hallazgos, módulos aceptados y proporción de incompatibilidades resueltas automáticamente.

Los saltos consecutivos y los de varias versiones se reportan por separado. Las transformaciones deterministas se distinguen de las asistidas. Un módulo solo se registra como aceptado si instala, supera sus pruebas sin alterarlas y satisface la verificación de R3.
