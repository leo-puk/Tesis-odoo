# Experimento g02 (16.0->17.0)

- Modulos: product_variant_sale_price, product_cost_price_avco_sync, account_credit_control, hr_timesheet_employee_analytic_tag, mail_notification_custom_subject
- Dependencias core: account, base, hr_timesheet, mail, sale, stock_account · OCA: account_analytic_tag
- Iteraciones: 20 · casuisticas: 42 · hunks: 70 (aplicados 29, pendientes 41)
- Resultado por fase: install=ok, upgrade=ok, test=ok

## Modulos

| modulo | repo | [MIG] | fecha | hunks | aplicados | [FIX] post |
|---|---|---|---|---|---|---|
| product_variant_sale_price | product-variant | 779e7d509b | 2024-03-05 | 18 | 5 | 3 |
| product_cost_price_avco_sync | stock-logistics-workflow | a44ffaeefe | 2025-04-14 | 7 | 6 | 0 |
| account_credit_control | credit-control | 0c8e247ddc | 2024-09-14 | 32 | 14 | 12 |
| hr_timesheet_employee_analytic_tag | timesheet | ff75647ec0 | 2025-06-30 | 8 | 1 | 0 |
| mail_notification_custom_subject | social | fde4ba078a | 2024-04-09 | 5 | 3 | 1 |

## Iteraciones

| it | fase | res | rc | s | err | avisos | log |
|---|---|---|---|---|---|---|---|
| 1 | install | FALLA | 255 | 2.4 | 2 | 0 | runs/exp-g02/01-install.log |
| 2 | install | FALLA | 255 | 2.3 | 2 | 0 | runs/exp-g02/02-install.log |
| 3 | install | FALLA | 255 | 3.8 | 2 | 0 | runs/exp-g02/03-install.log |
| 4 | install | FALLA | 255 | 2.8 | 2 | 0 | runs/exp-g02/04-install.log |
| 5 | install | FALLA | 255 | 3.0 | 2 | 0 | runs/exp-g02/05-install.log |
| 6 | install | FALLA | 255 | 69.9 | 2 | 12 | runs/exp-g02/06-install.log |
| 7 | install | FALLA | 255 | 85.3 | 2 | 12 | runs/exp-g02/07-install.log |
| 8 | install | FALLA | 255 | 80.4 | 2 | 13 | runs/exp-g02/08-install.log |
| 9 | install | FALLA | 255 | 81.1 | 2 | 12 | runs/exp-g02/09-install.log |
| 10 | install | FALLA | 255 | 79.3 | 2 | 12 | runs/exp-g02/10-install.log |
| 11 | install | FALLA | 255 | 75.6 | 2 | 12 | runs/exp-g02/11-install.log |
| 12 | install | FALLA | 255 | 89.0 | 2 | 11 | runs/exp-g02/12-install.log |
| 13 | install | FALLA | 255 | 89.1 | 2 | 11 | runs/exp-g02/13-install.log |
| 14 | upgrade | OK | 0 | 190.6 | 0 | 26 | runs/exp-g02/14-upgrade.log |
| 15 | test | FALLA | 255 | 145.4 | 2 | 11 | runs/exp-g02/15-test.log |
| 16 | install | FALLA | 255 | 142.7 | 2 | 11 | runs/exp-g02/16-install.log |
| 17 | install | OK | 0 | 155.9 | 0 | 10 | runs/exp-g02/17-install.log |
| 18 | upgrade | OK | 0 | 194.9 | 0 | 26 | runs/exp-g02/18-upgrade.log |
| 19 | test | FALLA | 1 | 120.3 | 2 | 10 | runs/exp-g02/19-test.log |
| 20 | test | OK | 0 | 113.2 | 0 | 10 | runs/exp-g02/20-test.log |

## Casuisticas

| id | modulo | fase | it | sev | cat | cob | guia | hunks | niv | sintoma |
|---|---|---|---|---|---|---|---|---|---|---|
| C001 | account_credit_control | install | 1 | bloqueante | A | L | G17-01 | 028 | 2 | Failed to load registry  |
| C002 | hr_timesheet_employee_analytic_tag | install | 1 | bloqueante | A | L | G17-01 | 058 | 2 | Failed to load registry  |
| C003 | mail_notification_custom_subject | install | 1 | bloqueante | A | L | G17-01 | 066 | 2 | Failed to load registry  |
| C004 | product_cost_price_avco_sync | install | 1 | bloqueante | A | L | G17-01 | 019 | 2 | Failed to load registry  |
| C005 | product_variant_sale_price | install | 1 | bloqueante | A | L | G17-01 | 005 | 2 | Failed to load registry  |
| C006 | account_credit_control | install | 6 | bloqueante | D | L | G17-07 | 046,047 | 1 | Failed to load registry  |
| C007 | account_credit_control | install | 7 | bloqueante | D | L | G17-07 | 048,049,050,051,052 | 1 | Failed to load registry  |
| C008 | account_credit_control | install | 8 | bloqueante | D | L | G17-06,G17-07 | 054,055,056,057 | 1 | Failed to load registry  |
| C009 | account_credit_control | install | 9 | bloqueante | D | L | G17-10 | 053 | 1 | Failed to load registry  |
| C010 | account_credit_control | install | 10 | bloqueante | C | R | - | 029 | 1 | Failed to load registry  |
| C011 | mail_notification_custom_subject | install | 11 | bloqueante | ? | R | - | 068,069 | 1 | Failed to load registry  |
| C012 | product_variant_sale_price | install | 12 | bloqueante | D | L | G17-07 | 018 | 1 | Failed to load registry  |
| C013 |  | install | 13 | bloqueante | B | R | - | - | - | Failed to load registry  |
| C014 |  | upgrade | 6 | aviso | ? | ? | - | - | - | /usr/lib/python3/dist-packages/odoo/fields.py:540: UserWarning: Since Odoo 17, property cr |
| C015 |  | upgrade | 6 | aviso | ? | ? | - | - | - | /usr/lib/python3/dist-packages/odoo/fields.py:540: UserWarning: Since Odoo 17, property cr |
| C016 |  | upgrade | 6 | aviso | ? | ? | - | - | - | /usr/lib/python3/dist-packages/odoo/fields.py:540: UserWarning: Since Odoo 17, property cr |
| C017 |  | upgrade | 6 | aviso | ? | ? | - | - | - | /usr/lib/python3/dist-packages/odoo/fields.py:540: UserWarning: Since Odoo 17, property cr |
| C018 |  | upgrade | 6 | aviso | ? | ? | - | - | - | /usr/lib/python3/dist-packages/odoo/fields.py:540: UserWarning: Since Odoo 17, property cr |
| C019 |  | upgrade | 6 | aviso | ? | ? | - | - | - | /usr/lib/python3/dist-packages/odoo/fields.py:540: UserWarning: Since Odoo 17, property cr |
| C020 |  | upgrade | 6 | aviso | ? | ? | - | - | - | /usr/lib/python3/dist-packages/odoo/fields.py:540: UserWarning: Since Odoo 17, property cr |
| C021 |  | upgrade | 6 | aviso | ? | ? | - | - | - | /usr/lib/python3/dist-packages/odoo/fields.py:540: UserWarning: Since Odoo 17, property cr |
| C022 |  | upgrade | 6 | aviso | ? | ? | - | - | - | /usr/lib/python3/dist-packages/odoo/fields.py:540: UserWarning: Since Odoo 17, property cr |
| C023 | account_credit_control | upgrade | 6 | aviso | B | ? | - | - | - | /usr/lib/python3/dist-packages/odoo/addons/base/models/ir_module.py:194: DeprecationWarnin |
| C024 | account_credit_control | upgrade | 14 | aviso | D | ? | G17-07 | - | - | Can't render custom view account_credit_control.partner_view_buttons for model res.partner |
| C025 | hr_timesheet_employee_analytic_tag | upgrade | 14 | aviso | D | ? | - | - | - | Can't render custom view hr_timesheet_employee_analytic_tag.hr_employee_view_form_inherit_ |
| C026 |  | upgrade | 14 | aviso | K | ? | - | - | - | Module Unknown: Not dropping the column of field __last_update of model credit.control.ana |
| C027 |  | upgrade | 14 | aviso | K | ? | - | - | - | Module Unknown: Not dropping the column of field __last_update of model credit.control.pol |
| C028 |  | upgrade | 14 | aviso | K | ? | - | - | - | Module Unknown: Not dropping the column of field __last_update of model credit.control.pri |
| C029 |  | upgrade | 14 | aviso | K | ? | - | - | - | Module Unknown: Not dropping the column of field __last_update of model credit.control.mar |
| C030 |  | upgrade | 14 | aviso | K | ? | - | - | - | Module Unknown: Not dropping the column of field __last_update of model credit.control.ema |
| C031 |  | upgrade | 14 | aviso | K | ? | - | - | - | Module Unknown: Not dropping the column of field __last_update of model res.partner.paymen |
| C032 |  | upgrade | 14 | aviso | K | ? | - | - | - | Module Unknown: Not dropping the column of field __last_update of model credit.control.run |
| C033 |  | upgrade | 14 | aviso | K | ? | - | - | - | Module Unknown: Not dropping the column of field __last_update of model credit.control.lin |
| C034 |  | upgrade | 14 | aviso | K | ? | - | - | - | Module Unknown: Not dropping the column of field message_main_attachment_id of model credi |
| C035 |  | upgrade | 14 | aviso | K | ? | - | - | - | Module Unknown: Not dropping the column of field __last_update of model credit.control.pol |
| C036 |  | upgrade | 14 | aviso | K | ? | - | - | - | Module Unknown: Not dropping the column of field __last_update of model credit.control.pol |
| C037 |  | upgrade | 14 | aviso | K | ? | - | - | - | Module Unknown: Not dropping the column of field __last_update of model credit.control.com |
| C038 |  | upgrade | 14 | aviso | K | ? | - | - | - | Module Unknown: Not dropping the column of field message_main_attachment_id of model credi |
| C039 |  | upgrade | 14 | aviso | K | ? | - | - | - | Module Unknown: Not dropping the column of field __last_update of model mail.message.custo |
| C040 |  | test | 13 | bloqueante | B | R | - | - | - | Failed to load registry  |
| C041 | product_variant_sale_price | install | 13 | bloqueante | B | R | - | 006,007,017 | 2 | Failed to load registry  |
| C042 | product_cost_price_avco_sync | test | 19 | bloqueante | B | C | - | 021,022,023,024,025 | 1 | ERROR: TestProductCostPriceAvcoSync.test_change_quantiy_price_xx |

### Por cobertura del estandar

| etiqueta | n | significado |
|---|---|---|
| ? | 26 | por codificar |
| L | 10 | listada en la guia OCA de la version |
| R | 5 | ninguna pieza del estandar la anticipa ('Do the rest of the changes') |
| C | 1 | la atrapa la CI (pre-commit o pruebas del modulo) |

### Por categoria

| cat | n | nombre |
|---|---|---|
| K | 14 | ruido |
| ? | 10 | sin clasificar |
| D | 7 | vistas |
| A | 5 | manifest y dependencias |
| B | 5 | API Python |
| C | 1 | modelo y ORM |

## Hunks pendientes que cambian comportamiento (candidatos a silenciosa)

Ningun error de install/upgrade/test los pidio.

| hunk | modulo | archivo | lineas | tags |
|---|---|---|---|---|
| 020 | product_cost_price_avco_sync | models/stock_picking.py | -2+4 | SIN_GUIA |
| 030 | account_credit_control | models/credit_control_communication.py | -0+1 | SIN_GUIA |
| 031 | account_credit_control | models/credit_control_communication.py | -6+5 | SIN_GUIA |
| 032 | account_credit_control | models/credit_control_line.py | -2+1 | SIN_GUIA |
| 033 | account_credit_control | models/credit_control_line.py | -5+2 | SIN_GUIA |
| 034 | account_credit_control | models/credit_control_line.py | -4+2 | SIN_GUIA |
| 035 | account_credit_control | models/credit_control_line.py | -2+1 | SIN_GUIA |
| 036 | account_credit_control | models/credit_control_policy.py | -3+1 | SIN_GUIA |
| 037 | account_credit_control | models/credit_control_policy.py | -1+1 | SIN_GUIA |
| 038 | account_credit_control | models/credit_control_run.py | -2+1 | SIN_GUIA |
| 039 | account_credit_control | models/credit_control_run.py | -2+1 | SIN_GUIA |
| 040 | account_credit_control | models/credit_control_run.py | -2+1 | SIN_GUIA |
| 041 | account_credit_control | models/mail_message.py | -2+2 | SIN_GUIA |
| 045 | account_credit_control | views/credit_control_line.xml | -6+6 | G17-07 |
| 061 | hr_timesheet_employee_analytic_tag | models/account_analytic_line.py | -2+2 | SIN_GUIA |
| 062 | hr_timesheet_employee_analytic_tag | models/account_analytic_line.py | -1+2 | SIN_GUIA |
| 063 | hr_timesheet_employee_analytic_tag | tests/test_hr_timesheet_employee_analytic_tag.py | -13+6 | G17-14 |
| 064 | hr_timesheet_employee_analytic_tag | tests/test_hr_timesheet_employee_analytic_tag.py | -1+1 | SIN_GUIA |
| 065 | hr_timesheet_employee_analytic_tag | tests/test_hr_timesheet_employee_analytic_tag.py | -1+1 | SIN_GUIA |
| 067 | mail_notification_custom_subject | migrations/15.0.1.0.0/post-migration.py | -20+0 | G17-02 |
