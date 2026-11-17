# Experimento g01 (16.0->17.0)

- Modulos: stock_quant_manual_assign, server_action_mass_edit, sale_blanket_order, sale_financial_risk, fieldservice_isp_flow
- Dependencias core: base, sale, sale_management, stock, uom · OCA: account_financial_risk, base_territory, fieldservice, web_action_conditionable
- Iteraciones: 30 · casuisticas: 44 · hunks: 112 (aplicados 80, pendientes 32)
- Resultado por fase: install=ok, upgrade=ok, test=ok

## Modulos

| modulo | repo | [MIG] | fecha | hunks | aplicados | [FIX] post |
|---|---|---|---|---|---|---|
| stock_quant_manual_assign | stock-logistics-warehouse | e5b0e65240 | 2024-09-03 | 17 | 10 | 2 |
| server_action_mass_edit | server-ux | 1475e6beec | 2024-05-06 | 37 | 23 | 1 |
| sale_blanket_order | sale-workflow | e48f1b6acd | 2024-08-02 | 36 | 27 | 5 |
| sale_financial_risk | credit-control | 0c79ab7987 | 2024-06-18 | 15 | 13 | 3 |
| fieldservice_isp_flow | field-service | 7664af532d | 2024-04-19 | 7 | 7 | 0 |

## Iteraciones

| it | fase | res | rc | s | err | avisos | log |
|---|---|---|---|---|---|---|---|
| 1 | install | FALLA | 255 | 2.9 | 2 | 0 | runs/exp-g01/01-install.log |
| 2 | install | FALLA | 255 | 3.2 | 2 | 0 | runs/exp-g01/02-install.log |
| 3 | install | FALLA | 255 | 2.6 | 2 | 0 | runs/exp-g01/03-install.log |
| 4 | install | FALLA | 255 | 2.5 | 2 | 0 | runs/exp-g01/04-install.log |
| 5 | install | FALLA | 255 | 3.1 | 2 | 0 | runs/exp-g01/05-install.log |
| 6 | install | FALLA | 255 | 14.4 | 3 | 1 | runs/exp-g01/06-install.log |
| 7 | install | FALLA | 255 | 13.7 | 3 | 1 | runs/exp-g01/07-install.log |
| 8 | install | FALLA | 255 | 19.6 | 3 | 1 | runs/exp-g01/08-install.log |
| 9 | install | FALLA | 255 | 21.1 | 3 | 1 | runs/exp-g01/09-install.log |
| 10 | install | FALLA | 255 | 22.3 | 3 | 1 | runs/exp-g01/10-install.log |
| 11 | install | FALLA | 255 | 16.7 | 3 | 1 | runs/exp-g01/11-install.log |
| 12 | install | FALLA | 255 | 14.9 | 2 | 1 | runs/exp-g01/12-install.log |
| 13 | install | FALLA | 255 | 14.4 | 2 | 1 | runs/exp-g01/13-install.log |
| 14 | install | FALLA | 255 | 37.8 | 2 | 2 | runs/exp-g01/14-install.log |
| 15 | install | FALLA | 255 | 71.0 | 2 | 2 | runs/exp-g01/15-install.log |
| 16 | install | FALLA | 255 | 76.3 | 2 | 2 | runs/exp-g01/16-install.log |
| 17 | install | FALLA | 255 | 70.0 | 2 | 2 | runs/exp-g01/17-install.log |
| 18 | install | FALLA | 255 | 72.5 | 3 | 3 | runs/exp-g01/18-install.log |
| 19 | install | FALLA | 255 | 81.4 | 2 | 3 | runs/exp-g01/19-install.log |
| 20 | install | FALLA | 255 | 84.5 | 2 | 3 | runs/exp-g01/20-install.log |
| 21 | install | OK | 0 | 83.2 | 0 | 2 | runs/exp-g01/21-install.log |
| 22 | upgrade | OK | 0 | 141.6 | 0 | 13 | runs/exp-g01/22-upgrade.log |
| 23 | test | FALLA | 1 | 132.6 | 12 | 5 | runs/exp-g01/23-test.log |
| 24 | test | FALLA | 1 | 131.9 | 13 | 5 | runs/exp-g01/24-test.log |
| 25 | test | FALLA | 1 | 115.9 | 10 | 5 | runs/exp-g01/25-test.log |
| 26 | test | FALLA | 1 | 112.2 | 11 | 4 | runs/exp-g01/26-test.log |
| 27 | test | FALLA | 1 | 159.3 | 8 | 4 | runs/exp-g01/27-test.log |
| 28 | test | FALLA | 1 | 182.9 | 5 | 4 | runs/exp-g01/28-test.log |
| 29 | test | FALLA | 1 | 179.7 | 2 | 4 | runs/exp-g01/29-test.log |
| 30 | test | OK | 0 | 193.4 | 0 | 4 | runs/exp-g01/30-test.log |

## Casuisticas

| id | modulo | fase | it | sev | cat | cob | guia | hunks | niv | sintoma |
|---|---|---|---|---|---|---|---|---|---|---|
| C001 | fieldservice_isp_flow | install | 1 | bloqueante | A | L | G17-01 | 106 | 2 | Failed to load registry  |
| C002 | sale_blanket_order | install | 1 | bloqueante | A | L | G17-01 | 056 | 2 | Failed to load registry  |
| C003 | sale_financial_risk | install | 1 | bloqueante | A | L | G17-01 | 091 | 2 | Failed to load registry  |
| C004 | server_action_mass_edit | install | 1 | bloqueante | A | L | G17-01 | 021,022 | 2 | Failed to load registry  |
| C005 | stock_quant_manual_assign | install | 1 | bloqueante | A | L | G17-01 | 001,002 | 2 | Failed to load registry  |
| C006 | server_action_mass_edit | install | 6 | bloqueante | ? | L | G17-02 | 023 | 3 | Couldn't load module server_action_mass_edit  |
| C007 | server_action_mass_edit | install | 6 | bloqueante | ? | R | - | 024 | 3 | Couldn't load module server_action_mass_edit  |
| C008 | server_action_mass_edit | install | 6 | bloqueante | ? | R | - | 025 | 3 | Couldn't load module server_action_mass_edit  |
| C009 | server_action_mass_edit | install | 6 | bloqueante | ? | R | - | 026,027 | 3 | Couldn't load module server_action_mass_edit  |
| C010 | server_action_mass_edit | install | 6 | bloqueante | ? | R | - | 028 | 3 | Couldn't load module server_action_mass_edit  |
| C011 | server_action_mass_edit | install | 6 | bloqueante | ? | R | - | 046,047,048,049,050,051,052,053 | 3 | Couldn't load module server_action_mass_edit  |
| C012 | server_action_mass_edit | install | 12 | bloqueante | D | L | G17-07,G17-09 | 045 | 1 | Failed to load registry  |
| C013 | server_action_mass_edit | install | 13 | bloqueante | D | L | G17-07 | 054 | 1 | Failed to load registry  |
| C014 | fieldservice_isp_flow | install | 14 | bloqueante | D | L | G17-07 | 107,108,109,110,111,112 | 1 | Failed to load registry  |
| C015 | stock_quant_manual_assign | install | 15 | bloqueante | D | R | - | 011 | 1 | Failed to load registry  |
| C016 | sale_financial_risk | install | 16 | bloqueante | B | L | G17-04 | 092 | 1 | Failed to load registry  |
| C017 | sale_financial_risk | install | 17 | bloqueante | D | L | G17-07 | 104,105 | 1 | Failed to load registry  |
| C018 | sale_blanket_order | install | 18 | bloqueante | ? | L | G17-03 | 057,058,059,060,061,062,063,064,065,066,067 | 3 | Couldn't load module sale_blanket_order  |
| C019 | sale_blanket_order | install | 19 | bloqueante | D | L | G17-10 | 087 | 1 | Failed to load registry  |
| C020 | sale_blanket_order | install | 20 | bloqueante | D | L | G17-07,G17-09 | 077,078,079,080,081,082,083,084,085,086 | 1 | Failed to load registry  |
| C021 | fieldservice_isp_flow | install | 14 | aviso | B | ? | - | - | - | /usr/lib/python3/dist-packages/odoo/addons/base/models/ir_module.py:194: DeprecationWarnin |
| C022 | sale_financial_risk | install | 18 | aviso | E | ? | - | - | - | Module sale_stock demo data failed to install, installed without demo data  |
| C023 | sale_blanket_order | upgrade | 22 | aviso | ? | ? | - | - | - | Can't render custom view sale_blanket_order.view_order_form for model sale.order. Assuming |
| C024 | sale_blanket_order | upgrade | 22 | aviso | ? | ? | - | - | - | Can't render custom view sale_blanket_order.view_order_form_disable_adding_lines for model |
| C025 |  | upgrade | 22 | aviso | K | ? | - | - | - | Module Unknown: Not dropping the column of field __last_update of model sale.blanket.order |
| C026 |  | upgrade | 22 | aviso | K | ? | - | - | - | Module Unknown: Not dropping the column of field __last_update of model sale.blanket.order |
| C027 |  | upgrade | 22 | aviso | K | ? | - | - | - | Module Unknown: Not dropping the column of field __last_update of model sale.blanket.order |
| C028 |  | upgrade | 22 | aviso | K | ? | - | - | - | Module Unknown: Not dropping the column of field message_main_attachment_id of model sale. |
| C029 |  | upgrade | 22 | aviso | K | ? | - | - | - | Module Unknown: Not dropping the column of field __last_update of model sale.blanket.order |
| C030 |  | upgrade | 22 | aviso | K | ? | - | - | - | Module Unknown: Not dropping the column of field message_main_attachment_id of model sale. |
| C031 |  | upgrade | 22 | aviso | K | ? | - | - | - | Module Unknown: Not dropping the column of field __last_update of model assign.manual.quan |
| C032 |  | upgrade | 22 | aviso | K | ? | - | - | - | Module Unknown: Not dropping the column of field __last_update of model assign.manual.quan |
| C033 |  | upgrade | 22 | aviso | K | ? | - | - | - | Module Unknown: Not dropping the column of field __last_update of model mass.editing.wizar |
| C034 |  | upgrade | 22 | aviso | K | ? | - | - | - | Module Unknown: Not dropping the column of field __last_update of model ir.actions.server. |
| C035 | stock_quant_manual_assign | test | 23 | bloqueante | C | C | - | 013,014,015,016 | 1 | ERROR: TestStockQuantManualAssign.test_quant_assign_wizard |
| C036 | stock_quant_manual_assign | test | 24 | bloqueante | B | C | - | 008,009,010 | 1 | ERROR: TestStockQuantManualAssign.test_quant_assign_wizard |
| C037 | sale_financial_risk | test | 23 | bloqueante | ? | C | - | 093 | 1 | ERROR: TestPartnerSaleRisk.test_compute_risk_amount |
| C038 | sale_financial_risk | test | 26 | bloqueante | ? | C | - | 095,096,097,098,099,100,101 | 1 | FAIL: TestPartnerSaleRisk.test_compute_risk_amount |
| C039 | sale_blanket_order | test | 23 | bloqueante | B | C | - | 071,072,073,074 | 1 | ERROR: TestSaleBlanketOrders.test_01_create_blanket_order |
| C040 | server_action_mass_edit | test | 23 | bloqueante | ? | C | - | 040,041,042,043,044 | 1 | FAIL: TestMassEditing.test_mass_edit_m2m_categ |
| C041 | sale_financial_risk | test | 26 | bloqueante | B | C | - | 102 | 1 | ERROR: TestRiskSalePayment.test_payment_risk_bypass |
| C042 |  | test | 23 | aviso | B | ? | - | - | - | /usr/lib/python3/dist-packages/odoo/addons/base/models/ir_module.py:194: DeprecationWarnin |
| C043 |  | test | 23 | aviso | D | ? | G17-06 | - | - | Using active_id, active_ids and active_model in expressions is deprecated, found active_id |
| C044 | sale_blanket_order | test | 23 | aviso | B | ? | G17-03 | - | - | /mnt/extra-addons/sale_blanket_order/tests/test_sale_order.py:148: DeprecationWarning: Sin |

### Por cobertura del estandar

| etiqueta | n | significado |
|---|---|---|
| ? | 17 | por codificar |
| L | 14 | listada en la guia OCA de la version |
| C | 7 | la atrapa la CI (pre-commit o pruebas del modulo) |
| R | 6 | ninguna pieza del estandar la anticipa ('Do the rest of the changes') |

### Por categoria

| cat | n | nombre |
|---|---|---|
| ? | 12 | sin clasificar |
| K | 10 | ruido |
| D | 8 | vistas |
| B | 7 | API Python |
| A | 5 | manifest y dependencias |
| E | 1 | datos XML/CSV y seguridad |
| C | 1 | modelo y ORM |

## Hunks pendientes que cambian comportamiento (candidatos a silenciosa)

Ningun error de install/upgrade/test los pidio.

| hunk | modulo | archivo | lineas | tags |
|---|---|---|---|---|
| 005 | stock_quant_manual_assign | models/__init__.py | -1+0 | SIN_GUIA |
| 006 | stock_quant_manual_assign | models/stock_picking_type.py | -14+0 | SIN_GUIA |
| 012 | stock_quant_manual_assign | views/stock_picking_type_views.xml | -16+0 | G17-07 |
| 017 | stock_quant_manual_assign | wizard/assign_manual_quants_view.xml | -1+1 | G17-09 |
| 038 | server_action_mass_edit | static/src/js/record.esm.js | -0+29 | SIN_GUIA |
| 039 | server_action_mass_edit | static/src/js/static_list.esm.js | -0+31 | SIN_GUIA |
| 068 | sale_blanket_order | models/sale_orders.py | -2+2 | SIN_GUIA |
| 075 | sale_blanket_order | tests/test_sale_order.py | -1+0 | G17-03 |
| 076 | sale_blanket_order | tests/test_sale_order.py | -2+1 | G17-03 |
| 088 | sale_blanket_order | views/sale_order_views.xml | -1+1 | G17-07,G17-09 |
| 089 | sale_blanket_order | wizard/create_sale_orders.py | -1+2 | SIN_GUIA |
| 090 | sale_blanket_order | wizard/create_sale_orders.py | -1+1 | SIN_GUIA |
| 094 | sale_financial_risk | models/sale.py | -1+1 | SIN_GUIA |
| 103 | sale_financial_risk | views/res_config_settings.xml | -9+5 | G17-10 |
