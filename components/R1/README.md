# Componente R1 — Perfil de migrabilidad

## Alcance

Este paquete contendrá exclusivamente la implementación del perfil de migrabilidad por módulo e instalación. Debe agregar la evidencia producida por R2 y la detección de R4 para anticipar incompatibilidades, construir el grafo de acoplamiento y clasificar si permanece trabajo manual.

## Fuente metodológica

Antes de implementar, se deben leer las secciones canónicas:

- `consulta-tesis/01.02.04-mapeo-de-objetivos-resultados-y-verificacion.md`
- `consulta-tesis/01.03.03.04-r1-oe-i-perfil-de-migrabilidad.md`

## Entradas previstas

- módulos e instalación que se evaluarán;
- hallazgos por capa y evidencia recuperada;
- dependencias declaradas e inferidas;
- resultados comparables de `odoo-bin upgrade_code` y `odoo-module-migrator`.

## Salidas previstas

- perfil trazable por módulo e instalación;
- grafo y unidades de acoplamiento;
- incompatibilidades anticipadas;
- clasificación de trabajo manual;
- datos necesarios para calcular cobertura, precisión, exactitud y comparación de McNemar.

## Límite de código

Todo el código de R1 debe permanecer dentro de este paquete. No se implementará un `run()` público hasta aprobar su contrato de entradas, salidas, errores y evidencia. Los experimentos y sus resultados pertenecen a `experiments/r1`, no a este paquete.
