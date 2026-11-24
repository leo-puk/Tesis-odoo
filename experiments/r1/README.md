# Experimentos R1

Este directorio conserva únicamente la evidencia experimental del perfil de migrabilidad.

- `variants/`: configuraciones o métodos comparados, incluida la configuración de la herramienta y las líneas base.
- `logs/`: registros inmutables de cada ejecución, con SHA del código, versiones, comando y entorno.
- `results/`: resultados estructurados, tablas agregadas e intervalos calculados a partir de ejecuciones registradas.

Los resultados deben permitir reconstruir cobertura de anticipación, precisión, exactitud de clasificación, intervalos de Wilson y la comparación exacta de McNemar. La muestra final no puede utilizarse para ajustar el método. Cada artefacto debe identificar el MIG correspondiente de `experiments/population`.
