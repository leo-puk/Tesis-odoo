# Componente R4 — Migración multicapa

## Alcance

Este paquete contendrá R4.1, detector estático de incompatibilidades, y R4.2, migración multicapa mediante reglas deterministas y asistencia de un modelo de lenguaje para el remanente que no admita una regla.

## Fuente metodológica

Antes de implementar, se deben leer las secciones canónicas:

- `consulta-tesis/01.02.04-mapeo-de-objetivos-resultados-y-verificacion.md`
- `consulta-tesis/01.03.03.02-r4-oe-iv-migracion-multicapa-automatizada.md`

## Entradas previstas

- módulos y salto de versión;
- orden y unidades de migración derivados del acoplamiento;
- evidencia recuperada por R2;
- reglas deterministas y configuración fija del modelo;
- líneas base `odoo-bin upgrade_code` y `odoo-module-migrator`.

## Salidas previstas

- hallazgos trazables para Python, XML, datos y manifiesto;
- transformaciones deterministas;
- propuestas asistidas con solicitud, respuesta y versión del modelo registradas;
- módulos migrados;
- evidencia de instalación, pruebas y verificación por R3;
- datos para precisión, cobertura y resolución automática.

## Límite de código

La detección debe poder evaluarse separada de la transformación. Todo el código de R4 debe permanecer en este paquete. No se implementará un `run()` público hasta aprobar el contrato de R4.1 y R4.2. Los experimentos pertenecen a `experiments/r4`.
