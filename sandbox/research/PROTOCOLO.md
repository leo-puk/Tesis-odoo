# Protocolo experimental — casuisticas de migracion de modulos Odoo (16.0 → 17.0)

Acordado el 2026-10-09. Implementado en `control/odoolab/{census,casuistics,experiment}.py`.

## Pregunta

Que errores aparecen al llevar un modulo OCA de 16.0 a 17.0, en que fase aparecen,
cuanto cuesta corregirlos, y **cuales cubre la metodologia existente y cuales no**.

## Condicion de control: el estandar existente

No se inventa un procedimiento: se aplica el que ya existe y se mide donde se queda corto.

| # | pieza | fuente |
|---|---|---|
| E1 | guia "Migration to version 17.0": `format-patch \| git am`, pre-commit, lista de tareas | OCA maintainer-tools wiki |
| E2 | herramientas sugeridas: `odoo-module-migrator`, `views_migration_17` | OCA |
| E3 | datos del core: OpenUpgrade (`upgrade_analysis` + scripts) | OCA |
| E4 | aceptacion de PR: CI verde con las pruebas del modulo | OCA CONTRIBUTING |
| E5 | "Upgrade a customized database" + checklist de pruebas | Odoo S.A. |
| E6 | `IntegrityCase` (invariantes antes/despues escritos a mano) | odoo/upgrade-util |

## Unidad de observacion: la casuistica

Ficha: modulo, salto, fase, sintoma (firma normalizada del log), ubicacion, categoria,
severidad, hunks humanos que la resuelven, lineas, iteracion en que aparece (enmascaramiento).

**Cobertura del estandar** (resultado central para OE II):

| etiqueta | significado |
|---|---|
| L | listada en la guia OCA 17.0 |
| A | la resuelve una herramienta automatica |
| U | la cubre OpenUpgrade |
| C | la atrapa la CI (pre-commit o pruebas del modulo) |
| V | solo la verificacion manual que recomienda Odoo |
| R | nada del estandar la anticipa ("Do the rest of the changes") |
| S | silenciosa: pasa todo, solo la ve el oraculo diferencial o un `[FIX]` posterior |

Taxonomia inicial de categorias: A manifest/dependencias · B API Python · C modelo/ORM ·
D vistas · E datos XML/CSV/seguridad · F JS/OWL · G reportes QWeb · H migracion de datos ·
I ecosistema · J pruebas · K ruido. Se refina con los datos (codificacion abierta → axial).

## Corpus

- **Poblacion**: todo modulo de un repo OCA con commit `[MIG] <modulo>: Migration to 17.0`
  en la rama 17.0 (`odoolab census`).
- **Muestra**: 1 piloto + 5, estratificados por dependencias (core / OCA), tamano del `[MIG]`,
  vistas / JS / reportes / pruebas, y con y sin `[FIX]` posterior al `[MIG]`.
- **Verdad de referencia**: el `[MIG]` humano partido en hunks, y los `[FIX]` posteriores.

## Procedimiento por modulo

1. `exp prepare` — S0 = padre del `[MIG]` (el modulo tras los pasos mecanicos de E1);
   hunks del `[MIG]`; dependencias core y OCA (las OCA ya migradas).
2. `exp seed` — plantillas de produccion v16 propias: con el modulo y sin el (linea base).
3. `exp baseline` — cada fase sin el modulo; sus firmas se descuentan.
4. Bucle: `exp run <fase>` → primer error nuevo → `exp fix --event <sig> --hunks <ids>`
   (se aplica **el hunk humano**, no una correccion propia) → repetir. Fases: `install`
   (BD vacia), `upgrade` (plantilla v16 + OpenUpgrade), `test` (`--test-enable`).
5. Verificacion E5 y oraculo diferencial v16 vs v17 sobre los datos del modulo.
6. Hunks que ningun error pidio → candidatos a casuistica silenciosa; se contrastan con
   los `[FIX]` posteriores.
7. Repetir con `odoo-module-migrator` aplicado sobre S0 para medir la etiqueta A.

## Amenazas a la validez

- Los datos demo no representan produccion → seeds por modulo cuando haga falta.
- Sesgo de supervivencia: solo modulos que alguien ya migro.
- El `[MIG]` humano es *una* migracion correcta, no la unica; las casuisticas son las de esa.
- El tiempo de aplicar un hunk no es esfuerzo humano: el proxy es lineas e iteraciones.
- Clasificacion: un segundo codificador sobre ≥20 % de las casuisticas (kappa de Cohen).
- `[FIX]` posterior es cota superior de defectos hasta codificarlo a mano.
