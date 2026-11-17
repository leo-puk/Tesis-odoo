# Precisiones de R2: componente acquisition

## Responsabilidad

Este componente recibe enlaces, descarga información y la guarda temporalmente. No identifica módulos ni versiones, descubre fuentes, determina relevancia, normaliza, compacta, consulta, evalúa o aplica arreglos. Estas tareas pertenecen a otros componentes.

## Fuentes permitidas y excluidas

Se permiten las soluciones de migración de módulos oficiales de Odoo, incluyendo scripts de OpenUpgrade, PR fusionados, comentarios, documentación y diferencias. Se excluye información específica de addons OCA, independientemente del repositorio donde aparezca. No hay splits de entrenamiento o evaluación; la evaluación tiene código separado.

OpenUpgrade documenta los scripts oficiales en openupgrade_scripts/scripts y sitúa las migraciones de addons OCA en los propios addons. Esto no significa que el repositorio completo carezca de información específica OCA: en la rama 16.0, openupgrade_scripts/apriori.py incluye renombrados y fusiones de addons OCA, por ejemplo mass_editing a server_action_mass_edit y account_reconciliation_widget a account_reconcile_oca. Este archivo mixto no debe admitirse completo bajo la política fija.

La inspección posterior confirmó bloques ejecutables específicos OCA dentro de scripts de módulos oficiales: base 16.0, mail 17.0 y hr_attendance 18.0, entre otros. Por eso no basta elegir carpetas oficiales. Véase analisis_openupgrade_y_matriz_pr.md para método, evidencia y límites.

Fuentes:
- https://oca.github.io/OpenUpgrade/070_migration_files.html
- https://raw.githubusercontent.com/OCA/OpenUpgrade/16.0/openupgrade_scripts/apriori.py
- https://github.com/OCA/OpenUpgrade/issues/2661

El seguimiento OCA/account-reconcile/issues/919 corresponde a addons OCA, no a módulos oficiales. Debe excluirse. Los comentarios se admiten o excluyen según el módulo al que corresponden. Los FIX de módulos oficiales se admiten.

Fuente: https://github.com/OCA/account-reconcile/issues/919

Decisión actual: no habrá interruptor. La exclusión de información específica de addons OCA será una política fija. Su cumplimiento integral todavía no está implementado. No se afirma ausencia de filtraciones. La política de procedencia es distinta de los criterios de relevancia del componente posterior.

## Descarga

capture_plan recibe un JSON con entradas id, kind y files: un mapa de nombres de archivo relativos a enlaces. Guarda bytes originales, sin normalización ni before/after. Para kind github_diff utiliza GitHubMetadata.compare_diff(url) mediante la API REST de GitHub.

Ejemplo:

```json
[
  {
    "id": "odoo-diff",
    "kind": "github_diff",
    "files": {
      "changes.diff": "https://github.com/odoo/odoo/compare/16.0...17.0"
    }
  }
]
```

## Criterios y normalización

No se aplican criterios de relevancia o selección académica al descargar. Se retiraron las etiquetas requires_six_criteria_review y maintainer_status, sin criterios implementados que las sustentaran. La normalización corresponde al siguiente componente; se retiró su importación y ejecución de adquisición. También se retiró split=construction.

## PR y temporales pendientes

La política final de captura de PR queda pendiente de la decisión del autor tras revisar la matriz. El método pull conserva metadatos. Otro componente decidirá cuándo borrar temporales; adquisición debe ofrecer una función invocable de eliminación, todavía pendiente. El autor propone chunks de diff en archivos, pero la unidad mínima y su correspondencia con las capturas no están definidas. No se exige caducidad automática ni crear chunks dentro de adquisición.

## Trazabilidad

Se conservan URL, fecha y hashes. El autor retira la exigencia de revisiones inmutables; la tesis debe ajustarse. Esto no excluye el contenido de revisiones de PR permitidos.

## Python

Python 3.12.13 instalado localmente en .python; entorno de ejecución creado en .venv. .python-version fija 3.12 y .vscode/settings.json selecciona .venv/Scripts/python.exe para nuevas selecciones de intérprete. No se cambió el Python global.

Ejecutar desde la raíz:

```powershell
& ./.venv/Scripts/python.exe --version
& ./.venv/Scripts/python.exe -m unittest discover -s tests -v
```

## Análisis complementario

El informe analisis_openupgrade_y_matriz_pr.md presenta la inspección interna 16–19 y las 36 combinaciones de PR, distinguiendo evidencia confirmada de casos no confirmados. OCA/account-reconcile/issues/919 permanece explícitamente excluido. Los datos en research son evidencia de auditoría, no fuentes del corpus de R2.

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

## Especificación implementada vigente

El backlog aprobado y su estado de implementación están en [backlog_adquisition.md](backlog_adquisition.md). Ese documento sustituye las propuestas históricas de este archivo. Incluye temp_data, documentos completos, conversión textual, catálogo obligatorio, exclusión fija, PR fusionados, ID simple, log y eliminación invocable. La exclusión depende de la cobertura del catálogo; no se declara una garantía absoluta de ausencia de filtraciones.
