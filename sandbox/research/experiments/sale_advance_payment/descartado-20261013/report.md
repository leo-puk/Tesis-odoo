# Experimento sale_advance_payment (16.0->17.0)

- Modulos: sale_advance_payment
- Dependencias core: sale · OCA: -
- Iteraciones: 7 · casuisticas: 5 · hunks: 16 (aplicados 16, pendientes 0)
- Resultado por fase: upgrade=sin_resolver, test=falla_sin_evento

## Modulos

| modulo | repo | [MIG] | fecha | hunks | aplicados | [FIX] post |
|---|---|---|---|---|---|---|
| sale_advance_payment | sale-workflow | a33a007535 | 2024-07-23 | 16 | 16 | 0 |

## Iteraciones

| it | fase | res | rc | s | err | avisos | log |
|---|---|---|---|---|---|---|---|
| 1 | install | FALLA | 255 | 4.0 | 2 | 0 | runs/exp-sale_advance_payment/01-install.log |
| 2 | install | FALLA | 255 | 4337.9 | 2 | 2 | runs/exp-sale_advance_payment/02-install.log |
| 3 | install | OK | 0 | 52.6 | 0 | 1 | runs/exp-sale_advance_payment/03-install.log |
| 4 | upgrade | FALLA | 0 | 86.4 | 1 | 3 | runs/exp-sale_advance_payment/04-upgrade.log |
| 5 | test | FALLA | 1 | 70.8 | 4 | 1 | runs/exp-sale_advance_payment/05-test.log |
| 6 | test | FALLA | 1 | 70.7 | 4 | 1 | runs/exp-sale_advance_payment/06-test.log |
| 7 | test | FALLA | 137 | 48.9 | 0 | 0 | runs/exp-sale_advance_payment/07-test.log |

## Casuisticas

| id | modulo | fase | it | sev | cat | cob | guia | hunks | niv | sintoma |
|---|---|---|---|---|---|---|---|---|---|---|
| C001 | sale_advance_payment | install | 1 | bloqueante | A | L | G17-01 | 001 | - | Failed to initialize database `x_sale_advance_payment_i`.  |
| C002 | sale_advance_payment | install | 2 | bloqueante | D | L | G17-07 | 008 | - | Failed to initialize database `x_sale_advance_payment_i`.  |
| C003 |  | upgrade | 4 | bloqueante | ? | R | - | - | - | FileNotFoundError: [Errno 2] No such file or directory: '/var/lib/odoo/filestore/x_sale_ad |
| C004 | sale_advance_payment | test | 5 | bloqueante | ? | C | - | 006,007 | 1 | FAIL: TestSaleAdvancePayment.test_01_sale_advance_payment |
| C005 | sale_advance_payment | test | 5 | bloqueante | ? | L | G17-07 | 002,003,004,005,009,010,011,012,013,014,015,016 | 3 | FAIL: TestSaleAdvancePayment.test_01_sale_advance_payment |

### Por cobertura del estandar

| etiqueta | n | significado |
|---|---|---|
| L | 3 | listada en la guia OCA de la version |
| R | 1 | ninguna pieza del estandar la anticipa ('Do the rest of the changes') |
| C | 1 | la atrapa la CI (pre-commit o pruebas del modulo) |

### Por categoria

| cat | n | nombre |
|---|---|---|
| ? | 3 | sin clasificar |
| A | 1 | manifest y dependencias |
| D | 1 | vistas |

## Hunks pendientes que cambian comportamiento (candidatos a silenciosa)

Ningun error de install/upgrade/test los pidio.

| hunk | modulo | archivo | lineas | tags |
|---|---|---|---|---|
