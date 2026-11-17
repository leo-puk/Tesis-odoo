# Experimento sale_advance_payment (16.0->17.0)

- Modulos: sale_advance_payment
- Dependencias core: sale · OCA: -
- Iteraciones: 10 · casuisticas: 10 · hunks: 16 (aplicados 14, pendientes 2)
- Resultado por fase: install=ok, upgrade=ok, test=ok

## Modulos

| modulo | repo | [MIG] | fecha | hunks | aplicados | [FIX] post |
|---|---|---|---|---|---|---|
| sale_advance_payment | sale-workflow | a33a007535 | 2024-07-23 | 16 | 14 | 4 |

## Iteraciones

| it | fase | res | rc | s | err | avisos | log |
|---|---|---|---|---|---|---|---|
| 1 | install | FALLA | 255 | 3.6 | 2 | 0 | runs/exp-sale_advance_payment/01-install.log |
| 2 | install | FALLA | 255 | 55.8 | 2 | 2 | runs/exp-sale_advance_payment/02-install.log |
| 3 | install | OK | 0 | 64.2 | 0 | 1 | runs/exp-sale_advance_payment/03-install.log |
| 4 | upgrade | OK | 0 | 88.8 | 0 | 3 | runs/exp-sale_advance_payment/04-upgrade.log |
| 5 | test | FALLA | 1 | 64.9 | 4 | 1 | runs/exp-sale_advance_payment/05-test.log |
| 6 | test | FALLA | 1 | 59.5 | 4 | 1 | runs/exp-sale_advance_payment/06-test.log |
| 7 | test | FALLA | 1 | 65.0 | 4 | 1 | runs/exp-sale_advance_payment/07-test.log |
| 8 | test | FALLA | 1 | 74.6 | 4 | 0 | runs/exp-sale_advance_payment/08-test.log |
| 9 | test | FALLA | 1 | 58.0 | 4 | 0 | runs/exp-sale_advance_payment/09-test.log |
| 10 | test | OK | 0 | 58.1 | 0 | 0 | runs/exp-sale_advance_payment/10-test.log |

## Casuisticas

| id | modulo | fase | it | sev | cat | cob | guia | hunks | niv | sintoma |
|---|---|---|---|---|---|---|---|---|---|---|
| C001 | sale_advance_payment | install | 1 | bloqueante | A | L | G17-01 | 001 | 2 | Failed to load registry  |
| C002 | sale_advance_payment | install | 2 | bloqueante | D | L | G17-07 | 008,009,010 | 1 | Failed to load registry  |
| C003 |  | install | 2 | aviso | ? | ? | - | - | - | /usr/lib/python3/dist-packages/odoo/fields.py:540: UserWarning: Since Odoo 17, property ac |
| C004 | sale_advance_payment | upgrade | 4 | aviso | ? | ? | - | - | - | Can't render custom view sale_advance_payment.view_order_form for model sale.order. Assumi |
| C005 |  | upgrade | 4 | aviso | K | ? | - | - | - | Module Unknown: Not dropping the column of field __last_update of model account.voucher.wi |
| C006 | sale_advance_payment | test | 5 | bloqueante | ? | C | - | 006,007 | 1 | FAIL: TestSaleAdvancePayment.test_01_sale_advance_payment |
| C007 | sale_advance_payment | test | 5 | bloqueante | ? | C | - | 002 | 3 | FAIL: TestSaleAdvancePayment.test_01_sale_advance_payment |
| C008 | sale_advance_payment | test | 5 | bloqueante | ? | C | - | 003 | 3 | FAIL: TestSaleAdvancePayment.test_01_sale_advance_payment |
| C009 | sale_advance_payment | test | 5 | bloqueante | ? | C | - | 004,005 | 3 | FAIL: TestSaleAdvancePayment.test_01_sale_advance_payment |
| C010 | sale_advance_payment | test | 5 | bloqueante | ? | C | - | 011,012,013,014 | 3 | FAIL: TestSaleAdvancePayment.test_01_sale_advance_payment |

### Por cobertura del estandar

| etiqueta | n | significado |
|---|---|---|
| C | 5 | la atrapa la CI (pre-commit o pruebas del modulo) |
| ? | 3 | por codificar |
| L | 2 | listada en la guia OCA de la version |

### Por categoria

| cat | n | nombre |
|---|---|---|
| ? | 7 | sin clasificar |
| A | 1 | manifest y dependencias |
| D | 1 | vistas |
| K | 1 | ruido |

## Hunks pendientes que cambian comportamiento (candidatos a silenciosa)

Ningun error de install/upgrade/test los pidio.

| hunk | modulo | archivo | lineas | tags |
|---|---|---|---|---|
| 015 | sale_advance_payment | wizard/sale_advance_payment_wzd_view.xml | -1+5 | G17-07 |
| 016 | sale_advance_payment | wizard/sale_advance_payment_wzd_view.xml | -0+1 | G17-07 |
