# Auditoría de OpenUpgrade y matriz de PR

Fecha: 16 de noviembre de 2026. Inspección de las ramas 16.0–19.0 mediante API pública y archivos del repositorio. Los datos de investigación están separados del componente y no constituyen su corpus consultable.

## Conclusión

Sí se puede extraer información exclusivamente oficial, pero no basta con seleccionar el repositorio o carpetas de módulos oficiales. Existen bloques que resuelven casos OCA dentro de esas carpetas. La separación requiere seleccionar archivos completos sin contenido OCA o preparar una vista oficial con bloques excluidos. La preparación de esa vista no corresponde a normalización ni relevancia del descargador: debe resolverse previamente y adquisición descargar únicamente los enlaces aprobados. Si solo existe un archivo mixto y no hay una fuente oficial separada, excluirlo completo es la opción que conserva el límite actual del componente.

## Método y límites

Se inspeccionaron árboles recursivos completos (truncated=false) de Odoo y OpenUpgrade en cuatro ramas. Se compararon nombres de directorios de scripts con manifiestos oficiales de Odoo 16–19. Se descargaron las cuatro ramas de OpenUpgrade y se buscaron nombres OCA identificados en apriori.py dentro de todos los archivos bajo openupgrade_scripts/scripts. Es una detección dirigida: puede producir falsos positivos y omitir addons no presentes en apriori.py. No demuestra ausencia total de información OCA ni equivalencia de módulos por compartir nombre. Las ramas son móviles; los SHA de árbol quedan registrados en audit.json. No se ejecutaron scripts descargados.

| Rama | Directorios de módulos | Archivos examinados | Directorios ausentes del inventario oficial combinado |
|---|---:|---:|---:|
| 16.0 | 386 | 783 | 0 |
| 17.0 | 439 | 828 | 0 |
| 18.0 | 432 | 837 | 0 |
| 19.0 | 332 | 758 | 0 |

El último indicador verifica nombres, no pureza del contenido. La revisión encontró contraejemplos concretos:

| Rama | Ubicación | Información específica OCA | Fuente |
|---|---|---|---|
|16.0|base/pre-migration.py|coupon_commercial_partner_applicability y website_sale_require_login|[Código](https://github.com/OCA/OpenUpgrade/blob/16.0/openupgrade_scripts/scripts/base/16.0.1.3/pre-migration.py)|
|17.0|mail/post-migration.py|Conversión de mail_activity_plan y mail_template_multi_attachment|[Código](https://github.com/OCA/OpenUpgrade/blob/17.0/openupgrade_scripts/scripts/mail/17.0.1.15/post-migration.py)|
|18.0|hr_attendance/post-migration.py|Conversión de hr_attendance_autoclose; su función migrate invoca esa adaptación|[Código](https://github.com/OCA/OpenUpgrade/blob/18.0/openupgrade_scripts/scripts/hr_attendance/18.0.2.0/post-migration.py)|
|19.0|account/pre-migration.py|Explicación sobre account_reconcile_oca|[Código](https://github.com/OCA/OpenUpgrade/blob/19.0/openupgrade_scripts/scripts/account/19.0.1.5/pre-migration.py)|

apriori.py también mezcla renombrados y fusiones oficiales y OCA. Los resultados íntegros y líneas detectadas están en content_audit.json. El hallazgo del término knowledge en una URL genérica de mass_mailing es un falso positivo; no se considera evidencia de un addon OCA.

## Extracción propuesta

1. Identificar módulos oficiales en el salto correspondiente, incluyendo los eliminados o renombrados.
2. Permitir archivos originales que contengan únicamente cambios oficiales.
3. Excluir archivos mixtos completos mientras no exista una vista oficial separada.
4. Si se necesita recuperar partes oficiales, preparar esa vista en otra etapa, preservando origen y fragmentos; no eliminar solo líneas con nombres OCA porque las operaciones pueden estar en funciones y llamadas separadas.
5. No seguir automáticamente enlaces a addons OCA desde documentación o comentarios.

No se implementó un extractor semántico ni se certificó una lista exhaustiva de archivos admisibles. El patrón de descarga puede mantenerse simple si recibe una lista previamente depurada. La política es fija, sin interruptor; no hay splits ni lógica de evaluación.

## Qué significa aplicado

Fusionado significa integrado en la rama base del PR, no instalado ni probado en el Odoo del partner. Cerrado no significa fusionado. Un PR cerrado sin fusión puede haber sido sustituido, aplicado por cherry-pick o integrado por otro mecanismo; su estado por sí solo no demuestra que la solución nunca se aplicara. En odoo/odoo conviene comprobar también el commit y el registro oficial de integración de Odoo.

Referencia: [API de PR](https://docs.github.com/en/rest/pulls/pulls).

## Matriz completa de combinaciones

La matriz cubre 3 ubicaciones × 3 estados × 2 relaciones con migración × 2 tipos de módulo = 36 combinaciones. C = caso confirmado; M = contenido OCA mixto confirmado en el repositorio, sin PR individual validado para esa celda; NC = no confirmado, no significa inexistente. La pertenencia debe revisarse en descripción, archivos y comentarios; no se deduce únicamente del repositorio. Infraestructura general es una clase adicional, no un módulo oficial ni un addon OCA.

| Repositorio | Estado | Migración | Módulo oficial | Addon OCA o contenido mixto OCA |
|---|---|---|---|---|
|odoo/odoo|Fusionado|Sí|C: [#15088](https://github.com/odoo/odoo/pull/15088)|NC|
|odoo/odoo|Fusionado|No|C: [#201629](https://mergebot.odoo.com/odoo/odoo/pull/201629), corrección tipográfica|NC|
|odoo/odoo|Abierto|Sí|C: [#289624](https://github.com/odoo/odoo/pull/289624)|NC|
|odoo/odoo|Abierto|No|NC|NC|
|odoo/odoo|Cerrado sin fusión|Sí|C: [#292289](https://github.com/odoo/odoo/pull/292289)|NC|
|odoo/odoo|Cerrado sin fusión|No|NC|NC|
|OCA/OpenUpgrade|Fusionado|Sí|C: [#6066](https://github.com/OCA/OpenUpgrade/pull/6066)|C: [#5807](https://github.com/OCA/OpenUpgrade/pull/5807), fusiona account_reconcile_model_oca en account_reconcile_oca|
|OCA/OpenUpgrade|Fusionado|No|NC|NC|
|OCA/OpenUpgrade|Abierto|Sí|C: [#5868](https://github.com/OCA/OpenUpgrade/pull/5868)|C: [#6082](https://github.com/OCA/OpenUpgrade/pull/6082), listado abierto, renombra addon OCA|
|OCA/OpenUpgrade|Abierto|No|NC|NC|
|OCA/OpenUpgrade|Cerrado sin fusión|Sí|C: [#5987](https://github.com/OCA/OpenUpgrade/pull/5987); account_reports, edición Enterprise; fuera de Community|M: bloques OCA detectados; estado del PR específico NC|
|OCA/OpenUpgrade|Cerrado sin fusión|No|NC|NC|
|Repositorios de addons OCA|Fusionado|Sí|NC|C: [account-reconcile #974](https://github.com/OCA/account-reconcile/pull/974)|
|Repositorios de addons OCA|Fusionado|No|NC|NC|
|Repositorios de addons OCA|Abierto|Sí|NC|C: [#1076](https://github.com/OCA/account-reconcile/pull/1076), listado abierto de account-reconcile|
|Repositorios de addons OCA|Abierto|No|NC|NC|
|Repositorios de addons OCA|Cerrado sin fusión|Sí|NC|NC|
|Repositorios de addons OCA|Cerrado sin fusión|No|NC|NC|

Los ejemplos de Odoo #15088 son históricos y sirven para mostrar el tipo de combinación, no para incluirlos en el corpus 16–19. El ejemplo account_reports muestra por qué oficial no implica Community. Los estados provienen de la consulta API o de la página individual y pueden cambiar.

La investigación no confirmó todas las celdas. La API limitó las consultas de account-reconcile (HTTP 403); las búsquedas negativas devolvieron los mismos resultados que las positivas y se descartaron como prueba de ausencia de migración. Por eso no se publican conteos de PR ni se presentan búsquedas por título como clasificación semántica. La matriz evita convertir ausencia de evidencia en inexistencia.

## Decisión de inclusión pendiente

| Contenido | Fusionado | Abierto | Cerrado sin fusión |
|---|---|---|---|
|Solución de migración exclusivamente oficial Community|Pendiente de decisión final sobre PR|Pendiente|Pendiente; comprobar integración alternativa|
|Oficial sin relación con migración|No demuestra contaminación; relevancia posterior|Igual|Igual|
|Específico de addon OCA o mixto inseparable|Excluir|Excluir|Excluir|
|Infraestructura general sin información específica OCA|Fuente potencial; no confundir con solución particular|Pendiente|Pendiente|

No se implementó la captura completa de PR mientras el autor revisa esta matriz.

## Eliminación y unidad mínima

El autor propone chunks de diff en archivos, pero la unidad mínima sigue pendiente. No se impone que toda fuente sea un diff: documentación, manifiestos y PR también son fuentes previstas. No se crean chunks en adquisición; el siguiente componente deberá definirlos y comunicar qué archivos temporales eliminar. La función de borrado debe recibir unidades identificadas y limitarse a archivos dentro del almacenamiento administrado. No se implementó borrado por chunks sin definir esa correspondencia.

## Separación de la investigación

Los archivos audit.json, content_audit.json, árboles JSON y tar.gz de esta carpeta son evidencia de esta revisión, contienen material excluido y NO deben incorporarse al corpus de R2.

## Evidencia web complementaria

- OpenUpgrade #5807 está fusionado y trata explícitamente addons OCA: https://github.com/OCA/OpenUpgrade/pull/5807
- El listado abierto muestra #6082 sobre renombrado OCA: https://github.com/OCA/OpenUpgrade/pulls
- El listado de account-reconcile muestra #1076 MIG y #1077 FIX; una etiqueta FIX no implica migración: https://github.com/OCA/account-reconcile/pulls
- Odoo #201629 es una corrección tipográfica fusionada: https://mergebot.odoo.com/odoo/odoo/pull/201629

## Confirmación posterior: scripts específicos OCA en OpenUpgrade

La inspección de código confirmó scripts ejecutables que transforman datos de addons OCA dentro de OpenUpgrade, no solamente menciones o mapas de renombrado:

- 18.0, hr_attendance/18.0.2.0/post-migration.py: la función _hr_attendance_autoclose convierte configuración y registros de hr_attendance_autoclose; migrate la invoca. Fuente: https://github.com/OCA/OpenUpgrade/blob/18.0/openupgrade_scripts/scripts/hr_attendance/18.0.2.0/post-migration.py
- 17.0, maintenance/17.0.1.0/post-migration.py: _maintenance_plan transforma solicitudes vinculadas a maintenance_plan usando su tabla y parámetros; migrate la invoca. Fuente: https://github.com/OCA/OpenUpgrade/blob/17.0/openupgrade_scripts/scripts/maintenance/17.0.1.0/post-migration.py
- 16.0, base/16.0.1.3/pre-migration.py: login_or_registration_required_at_checkout detecta website_sale_require_login y adapta la configuración oficial de checkout; migrate la invoca. Fuente: https://github.com/OCA/OpenUpgrade/blob/16.0/openupgrade_scripts/scripts/base/16.0.1.3/pre-migration.py

Esto acredita adaptaciones específicas de addons OCA, algunas para absorber funcionalidades en módulos oficiales; no acredita la migración completa del código de cada addon a otra versión. Tampoco demuestra qué caso concreto de la muestra resolvería sin conocer sus módulos.

Aplicando la condición indicada por el autor, OpenUpgrade queda descartado como fuente de R2. Esta decisión sustituye la propuesta anterior de extracción parcial. Deben retirarse de la tesis sus referencias como fuente de adquisición, incluyendo su documentación, scripts y PR bajo esta política. La exclusión aún no está aplicada en el código: validate_source_origin sigue aceptando openupgrade_analysis. Las copias en research/verified_scripts son evidencia de auditoría, no corpus de R2.

## Decisión vigente: excluir unidades mixtas completas

El autor decide excluir completos los archivos o documentos que mezclen información admisible con información específica de migración de addons OCA. No se separarán sus bloques para recuperarlos parcialmente. Esta decisión sustituye la exclusión total de OpenUpgrade indicada anteriormente: pueden considerarse unidades exclusivamente admisibles, previamente verificadas; no se admite un repositorio completo por su procedencia.

La unidad mínima de almacenamiento sigue pendiente de definición. Esta decisión no introduce fragmentación, normalización ni análisis de relevancia dentro de acquisition. La política todavía no está implementada integralmente en el código.

Aclaración: account-reconcile es un repositorio de la organización OCA que contiene addons de conciliación contable. El seguimiento citado era su issue 919, que enumera migraciones de esos addons a 19.0; se excluye por tratar directamente sus migraciones. Fuente: https://github.com/OCA/account-reconcile/issues/919

## Acuerdo vigente: unidad completa y separación de componentes

La unidad de información elegida, por ahora, es el documento o archivo completo. Acquisition es el primer componente: recibe enlaces, descarga y almacena unidades completas. Descarta desde el inicio los archivos o documentos mixtos que incluyan información directa sobre addons OCA junto con información admisible; no recupera bloques parciales. También permanece excluida la información dedicada específicamente a migraciones de addons OCA.

El siguiente componente comprime la información y extrae lo importante. Acquisition no crea chunks, resume ni selecciona por relevancia. La función de eliminación pendiente deberá operar sobre unidades completas identificadas; la decisión de cuándo eliminarlas proviene del componente coordinador.

Este acuerdo sustituye las propuestas anteriores de usar fragmentos o cambios documentados como unidad dentro de acquisition. El mecanismo que identifica y rechaza fuentes mixtas sigue pendiente de implementación; el acuerdo no constituye evidencia de que el código actual ya lo cumpla.
