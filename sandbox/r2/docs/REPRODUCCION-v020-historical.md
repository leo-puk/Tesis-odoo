# Reproducción de R2 0.2 desde entorno limpio

Se requiere Python 3.12, Git y los archivos del paquete. El entorno de referencia es Windows y se registra exactamente en audit/environment.json. No se instala en runtimes administrados: todo va a una carpeta .venv del proyecto. requirements-lock.txt fija las versiones efectivamente instaladas, incluidos paquetes de construcción. El paquete R2 se instala desde su código local, no desde PyPI.

```powershell
python3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip install --no-build-isolation --no-deps -e .
.\.venv\Scripts\python.exe -m r2 doctor
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Si se utiliza uv, `uv pip install --python .venv/Scripts/python.exe -r requirements-lock.txt` es equivalente para instalar las dependencias. Una configuración de red o índice restringida puede impedir descargar paquetes; no se sustituye NetworkX por el fallback para acreditar la entrega científica. El modo de compatibilidad se prueba por separado con R2_FORCE_COMPAT_BFS=1.

## Reconstruir sin red la colección capturada

El inventario activo es audit/corpus-normalized-v2/inventory.json y contiene nueve unidades de fuente/comparación parciales. Sus rutas a snapshots y originales son relativas al inventario, para trasladar la carpeta. Los bytes originales permanecen en corpus-capture y corpus19-supplement. La extracción activa v2 conserva espacios al final de línea y solo normaliza codificación/saltos; la extracción v1 histórica recortaba esos espacios y no se reutiliza como si fuera idéntica. El código comprueba los hashes originales y normalizados; no inventa SHA upstream para páginas mutables.

```powershell
.\r2.ps1 build audit/corpus-normalized-v2/inventory.json --audit-registry audit/assignments.json --db audit/reconstructed.sqlite
.\r2.ps1 inventory --db audit/reconstructed.sqlite
.\r2.ps1 export --db audit/reconstructed.sqlite > audit/reconstructed.json
```

El nombre de salida debe ser nuevo. La colección no se sobrescribe. Su identidad se deriva de contenido, revisiones, política y revisiones documentales, no de los tiempos de ejecución. Los candidatos de la captura general aún necesitan codificación: no se presentan como incompatibilidades confirmadas.

La reconstrucción ejecutada se conserva en audit/corpus-reconstructed.sqlite y produjo la misma revisión que audit/corpus-delivery.sqlite; audit/reconstruction-check.txt registra la igualdad. source-coverage.csv informa alcance por fuente; collection-counts.csv informa unidades y estados, no porcentajes de cobertura académica.

## Capturar de nuevo con red

```powershell
.\r2.ps1 capture-plan audit/capture-plan.json --output audit/new-capture
.\r2.ps1 capture-plan audit/capture-plan-19.json --output audit/new-capture-19
```

La primera captura documentó un HTTP 404 al buscar odoo/fields.py en 19.0. El segundo plan usa la ruta real odoo/orm/fields.py y conserva ese alcance parcial: en 19.0 los campos se distribuyen en varios archivos. No se compara una ruta normalizada ficticia ni se afirma cobertura completa. Los reportes de fallos permanecen como historial. Una captura nueva es otra revisión, aunque la rama tenga el mismo nombre.

La copia de guías y changelogs no incorpora soluciones de las migraciones reservadas. No obstante, la auditoría de posibles copias indirectas debe completarse antes de evaluar. Las licencias cuyo contenido exacto no se verificó figuran como no verificadas; no se infiere automáticamente la licencia del wiki a partir del repositorio.

## Metadatos GitHub y selección

```powershell
.\r2.ps1 github --query 'org:OCA is:pr is:merged "[MIG]" in:title base:17.0 created:2026-10-01..2026-10-31' --output audit/metadata-window
.\r2.ps1 github --repo OCA/REPOSITORIO --number NUMERO --output audit/pr-metadata
.\r2.ps1 sample audit/selection-input.json > audit/new-selection-status.json
```

Se admite GITHUB_TOKEN o GH_TOKEN por variable de entorno; nunca se pasa por línea de comandos, se escribe en inventarios o se muestra en errores. Sin token los límites son menores. Se archivan solo campos necesarios de metadatos, no cuerpos ni parches. Si una búsqueda supera 1000 o GitHub la marca incompleta, el cliente se detiene y exige particionar el intervalo/repositorio. Hay paginación por Link, detección de ciclos, comprobación de archivos y errores HTTP. No hay esperas automáticas largas ni se oculta un marco muestral incompleto.

La consulta real y los metadatos del piloto excluido están en audit/github-metadata-search y github-pilot-metadata. Además se capturaron 52 entradas de una ventana mensual en tres estratos: github-window-17/18/19. Son un marco parcial, no un censo completo. No se han completado los seis criterios ni el corte final. sample no genera aprobaciones, mantenedores ni hechos de selección.

## Revisiones y consulta

Consultar y revisar según MANUAL_CODIFICACION.md. Las anotaciones de 0.1 no satisfacen automáticamente el contrato de vigencia/condiciones de 0.2: deben revisarse, no aceptarse silenciosamente.

```powershell
.\r2.ps1 query RUTA_MODULO --module-name NOMBRE_TECNICO --db COLECCION --from 16.0 --to 17.0 --status verified --limit 10 --depth 3 --format json --timing-log timing.jsonl
.\r2.ps1 query RUTA_MODULO --module-name NOMBRE_TECNICO --db COLECCION --from 16.0 --to 17.0 --status verified --limit 10 --depth 3 --engine bm25
.\.venv\Scripts\python.exe -m examples.run_demo --output examples/output/new-v020-demo
```

La demostración utiliza el piloto como caso de construcción y revisión del desarrollador. No genera juicios independientes ni C1/P1/C2 empíricos. No ejecuta una migración y no altera el módulo.

## Evaluación

Completar personas, criterios, consultas y correspondencias reales en los instrumentos de docs/PROTOCOLO_EVALUACION.md y audit/protocol-template.json. `evaluate --development` solo comprueba instrumentos con datos de desarrollo; cada reporte conserva esa etiqueta.

```powershell
.\r2.ps1 freeze parameters.json --specification evaluation.json --selection selection.json --db COLECCION --output frozen-protocol.json
.\r2.ps1 evaluate evaluation.json --db COLECCION --repeats REPETICIONES --output-dir audit/measurement
```

freeze se niega a inventar una selección de treinta casos o responsables. Antes de la evaluación oficial deben coincidir fingerprint de código, colección, módulos originales, consultas, correspondencias, casos y parámetros. Pandas exporta las tablas y sklearn calcula únicamente cocientes cuya unidad coincide con la tesis; statsmodels no se emplea de forma decorativa.

## Historial y Word

docs/README-v010-historical.md, el piloto previo y los logs antiguos se conservan como antecedentes. No acreditan el código actual ni equivalencia funcional. audit/initial-state.json y el informe final registran la base Git y hashes. La revisión Git inicial es una base del repositorio, no un commit nuevo de R2. Los cambios del usuario quedan intactos. El Word se usa solo como fuente y se comprueba su SHA256 al cerrar el trabajo.
