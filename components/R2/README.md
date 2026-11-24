# Componente R2 — Información y consulta de migración

## Alcance

Este paquete contendrá R2.1 y R2.2. R2.1 comprende planificación, adquisición versionada, normalización, persistencia y cruce inicial. R2.2 comprende extracción de relaciones, recorrido, ordenación, consulta, reporte, CLI y evaluación frente a BM25.

## Fuente metodológica

Antes de implementar, se deben leer las secciones canónicas:

- `consulta-tesis/01.02.04-mapeo-de-objetivos-resultados-y-verificacion.md`
- `consulta-tesis/01.03.03.01-r2-1-y-r2-2-oe-ii-informacion-de-migracion-y-consulta-local.md`

## Entradas previstas

- fuentes oficiales y revisiones identificables;
- módulos, manifiestos y referencias técnicas;
- versiones de origen y destino;
- consultas y juicios de pertinencia fijados para la evaluación.

## Salidas previstas

- colección local estructurada y trazable;
- cruce inicial entre evidencia y elementos del addon;
- relaciones y caminos de evidencia;
- primera vista de hasta diez candidatos;
- salida estructurada y reporte de la CLI;
- datos para C1, P1, C2, V1 y T1 y la comparación con BM25.

## Límite de código

R2 recupera y estructura evidencia; no migra código ni certifica equivalencia funcional. Todo su código debe permanecer en este paquete. No se implementará un `run()` público hasta aprobar el contrato conjunto de R2.1 y R2.2. Los experimentos pertenecen a `experiments/r2`.
