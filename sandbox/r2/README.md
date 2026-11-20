# R2: guía de uso

R2 analiza addons de Odoo antes de migrarlos. Lee el código sin ejecutarlo, compara versiones, identifica coincidencias técnicas, recorre relaciones y genera reportes trazables. Es determinista: no usa IA, embeddings ni servicios de lenguaje.

## Requisitos

- Windows o Linux con Git.
- Python 3.12.
- Un checkout local de Odoo con las revisiones de origen y destino.
- Una carpeta con addons que contengan `__manifest__.py`.

## Instalación

Desde `sandbox/r2`:

```bash
py -3.12 -m venv .venv
./.venv/Scripts/python.exe -m pip install -e .
./.venv/Scripts/python.exe -m r2 --help
```

En Linux se reemplaza `./.venv/Scripts/python.exe` por `./.venv/bin/python`.

## Uso recomendado: asistente local R2.2

```bash
./.venv/Scripts/python.exe -m r2 start
```

El asistente:

1. Solicita o reutiliza la ruta del checkout local de Odoo.
2. Comprueba `odoo-bin` y Git.
3. Busca addons mediante `__manifest__.py` y los muestra numerados.
4. Permite escoger números, rangos, nombres o `all`.
5. Muestra las versiones disponibles localmente.
6. Genera el diff entre SHA locales, sin descargar el compare de GitHub.
7. Construye una colección SQLite y un reporte por addon.

La configuración se guarda en `%USERPROFILE%\.r2\config.json`. R2 no ejecuta `git fetch` ni modifica los repositorios analizados.

Ejemplo sin preguntas:

```bash
./.venv/Scripts/python.exe -m r2 start \
  --odoo "C:/repos/odoo" \
  --addons "C:/repos/addons-personalizados" \
  --from 16.0 --to 17.0 \
  --select "1,3-5" \
  --output-dir "temp_data/analisis-16-17"
```

Para revisar la detección sin analizar:

```bash
./.venv/Scripts/python.exe -m r2 start --list-only
```

## Salidas

| Ruta | Contenido |
|---|---|
| `collection.sqlite` | Colección normalizada compartida. |
| `local-source.json` | Repositorio, refs, SHA y tamaño del diff. |
| `bindings.json` | Versiones y revisiones de la fuente local. |
| `summary.json` | Resumen de toda la ejecución. |
| `addons/<addon>/report.txt` | Reporte legible del addon. |
| `addons/<addon>/report.json` | Reporte estructurado. |
| `addons/<addon>/crossing.json` | Coincidencias directas. |
| `addons/<addon>/relations.json` | Relaciones y caminos de evidencia. |

## Flujo web controlado

Sirve para incorporar documentación, PR y URL permitidas por catálogo:

```bash
./.venv/Scripts/python.exe -m r2 plan "C:/ruta/addon" --from 16.0 --to 17.0 \
  --catalog reference/adquisition-final/examples/catalog.json --output-dir temp_data/plan-nuevo

./.venv/Scripts/python.exe -m r2 run "C:/ruta/addon" --module-name addon_tecnico \
  --from 16.0 --to 17.0 --plan temp_data/plan-nuevo/plan.json \
  --catalog temp_data/plan-nuevo/catalog.json --bindings temp_data/plan-nuevo/bindings.json \
  --output-dir temp_data/ejecucion-nueva
```

`run` requiere HTTPS. Una captura fallida no demuestra ausencia de incompatibilidades; debe revisarse `inventory.json`.

## Consulta, validación y pruebas

```bash
./.venv/Scripts/python.exe -m r2 query "C:/ruta/addon" --module-name addon_tecnico \
  --db temp_data/analisis/collection.sqlite --from 16.0 --to 17.0 --depth 3 --limit 10

./.venv/Scripts/python.exe -m r2 validate-output temp_data/analisis/addons/addon_tecnico/report.json
./.venv/Scripts/python.exe -m r2 evaluate evaluacion.json --db temp_data/analisis/collection.sqlite --repeats 3
./.venv/Scripts/python.exe -m unittest discover -s tests -v
```

## Límites

- R2 entrega candidatos técnicos; no migra código ni certifica equivalencia funcional.
- Las revisiones y fuentes necesarias deben estar disponibles.
- Las referencias dinámicas pueden quedar sin resolver.
- El dashboard visual permanece pendiente; la salida vigente es TXT y JSON.

Véase [FUNCIONAMIENTO.md](FUNCIONAMIENTO.md) para la arquitectura y [PRODUCT_BACKLOG.md](PRODUCT_BACKLOG.md) para pendientes.
