# Componente R3 — Equivalencia funcional

## Alcance

Este paquete contendrá el mecanismo de verificación por equivalencia funcional entre las versiones de origen y destino. Debe combinar pruebas del módulo, casos diferenciales deterministas y detección de construcciones obsoletas.

## Fuente metodológica

Antes de implementar, se deben leer las secciones canónicas:

- `consulta-tesis/01.02.04-mapeo-de-objetivos-resultados-y-verificacion.md`
- `consulta-tesis/01.03.03.03-r3-oe-iii-mecanismo-de-verificacion-por-equivalencia-funcional.md`

## Entradas previstas

- módulo de origen y módulo migrado;
- entornos aislados de Odoo/PostgreSQL;
- datos de demostración controlados;
- incompatibilidades detectadas y comportamiento extendido;
- conjunto documentado de defectos con prueba de regresión.

## Salidas previstas

- resultados de las pruebas sin alterarlas;
- casos y observaciones diferenciales;
- divergencias silenciosas;
- construcciones obsoletas supervivientes;
- declaración de equivalencia acotada a los casos ejecutados;
- datos para sensibilidad y especificidad.

## Límite de código

R3 no debe invocar el modelo de lenguaje de R4. Todo su código debe permanecer en este paquete. No se implementará un `run()` público hasta aprobar su contrato de entornos, casos y evidencia. Los experimentos pertenecen a `experiments/r3`.
