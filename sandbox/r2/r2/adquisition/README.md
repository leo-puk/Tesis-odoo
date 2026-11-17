# Componente adquisition

Descarga unidades completas de fuentes previamente revisadas. Requiere Python 3.12;
no tiene dependencias externas. Véase backlog_adquisition.md para el contrato vigente.

## Uso

Editar examples/catalog.json para registrar enlaces exactos revisados en allowed_urls.
Actualizar oca_repositories y oca_addons para el corpus. El catálogo incluido es una
semilla, no un inventario completo. No contiene enlaces autorizados por defecto.

```powershell
& ./.venv/Scripts/python.exe -m adquisition capture examples/plan.json --catalog examples/catalog.json
& ./.venv/Scripts/python.exe -m adquisition delete SESSION_ID UNIT_ID
& ./.venv/Scripts/python.exe -m unittest discover -s tests -v
```

```python
from adquisition import capture_plan, delete_units
result = capture_plan('examples/plan.json', catalog_path='examples/catalog.json')
# El siguiente componente usa result['inventory'] para identificar unidades.
# Cuando corresponde: delete_units(result['session_id'], [unit_id])
```

--output indica temp_data o su directorio padre. Cada ejecución crea una sesión
independiente con inventory.json, acquisition.jsonl y carpetas de unidades aceptadas.
No se crean reportes aparte ni hashes de contenido.

## Plan

Cada entrada requiere id, kind y files (nombre simple a URL). Ejemplo:

```json
[{"id":"odoo-diff","kind":"github_diff","files":{"changes.diff":"https://github.com/odoo/odoo/compare/16.0...17.0"}}]
```

Tipos: official_manifest, official_documentation, oca_guidance, openupgrade_analysis,
github_diff y github_pr. PR usa https://github.com/OWNER/REPO/pull/NUMBER.
Un PR se guarda como JSON completo de sus recursos consultados más diff.
La documentación textual se guarda en TXT/MD. Binarios no soportados se excluyen.
Los diffs provienen del endpoint compare de GitHub, con su semántica de ancestro común.

Estados: accepted, excluded, incomplete, failed y deleted. No se incorporan fuentes
excluidas o incompletas al almacenamiento de unidades aceptadas.

## Límites

La exclusión es determinística y depende del catálogo revisado. No detecta soluciones
sin identificadores ni certifica ausencia de filtraciones. No se admite OpenUpgrade
completo: los archivos mixtos se excluyen completos. No se hacen búsquedas, rankings,
resúmenes, fragmentación o análisis del código del partner. La interfaz CLI es de
adquisición/borrado, no la consulta de R2.2. No hay escritores concurrentes por sesión.
Puede configurarse GITHUB_TOKEN o GH_TOKEN para llamadas GitHub. No se registran tokens.
