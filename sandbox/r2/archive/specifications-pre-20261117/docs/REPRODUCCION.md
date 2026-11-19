# Reproducción R2 0.3

Usar Python 3.12 y el entorno `.venv` del proyecto. Dependencias fijadas en `requirements-lock.txt`. El paquete final de adquisición usa la biblioteca estándar; el motor R2 utiliza además NetworkX, lxml, pandas y scikit-learn. statsmodels sigue sin función inferencial justificada.

## Demostración verificable sin internet

```powershell
.\.venv\Scripts\python.exe -m examples.run_session_demo --output examples/output/v030-session
.\r2.ps1 query examples/output/v030-session/module --db examples/output/v030-session/collection.sqlite --from 16.0 --to 17.0 --format json
```

Se generan plan, catálogo sintético, bindings, capturas temporales, colección, módulo sintético, query.json y run.json. Es un caso de ingeniería, no una fuente real ni un resultado de tesis. Elegir otra carpeta si la salida ya existe.

## Captura real y construcción

1. Copiar y revisar `reference/adquisition-final/examples/plan.json` y `catalog.json`. Autorizar únicamente enlaces exactos revisados; completar exclusiones. Los ejemplos no autorizan enlaces por defecto.
2. Preparar bindings externos con versiones y referencias: `examples/session-bindings.json` ilustra el plan `odoo-diff`. Añadir bindings para todas las unidades aceptadas.
3. Ejecutar:

```powershell
.\r2.ps1 capture-plan PLAN.json --catalog CATALOGO.json --output temp_data
.\r2.ps1 build temp_data/SESION/inventory.json --bindings BINDINGS.json --db COLECCION_NUEVA.sqlite
.\r2.ps1 inventory --db COLECCION_NUEVA.sqlite
.\r2.ps1 export --db COLECCION_NUEVA.sqlite
.\r2.ps1 query RUTA_MODULO --module-name NOMBRE_TECNICO --db COLECCION_NUEVA.sqlite --from 16.0 --to 17.0 --status candidate --format json
```

`--output` puede ser temp_data o su padre; adquisición devuelve la ruta real de sesión. Estado `accepted` no equivale a cambio `verified`. Una colección nueva exige revisión de sus cambios antes de consultar con `--status verified`; se reconstruye con `--annotations REVISIONES.json` hacia otra base.

## Eliminación y persistencia

```powershell
.\r2.ps1 delete-units SESION UNIDAD_1 UNIDAD_2 --output temp_data
```

Eliminar solo cuando corresponda, después de construir y verificar los artefactos derivados. La colección conserva los archivos consumidos y ya permite consultar sin temporales. No hay borrado automático.

## Selección y evaluación independientes

```powershell
.\r2.ps1 evaluation-metadata --query 'org:OCA is:pr is:merged "[MIG]" in:title base:17.0' --output audit/NUEVOS_METADATOS
.\r2.ps1 sample audit/selection-input.json
```

Este cliente conserva campos de metadatos sin cuerpos ni parches; no se reemplaza por la captura completa de PR del componente final. Se admiten GITHUB_TOKEN o GH_TOKEN por entorno. No se registran tokens.

La evaluación de ingeniería admite `evaluate ... --development`; no es una evaluación académica. La definitiva requiere responsables, juicios, selección y protocolo congelado, además de auditoría de asignaciones. Las colecciones nuevas no reciben esa aprobación automáticamente. Los fingerprints de código incluyen ahora los subpaquetes; los protocolos antiguos necesitan una nueva congelación revisada.

## Compatibilidad histórica

`build-legacy INVENTARIO_ANTIGUO --audit-registry REGISTRO --db OTRA_BASE` reconstruye explícitamente fuentes locales históricas con la política fija. Los comandos anteriores `github`, el interruptor OCA y `build` sin bindings se sustituyeron. Las bases existentes no se sobrescriben; no se garantiza conservar los fingerprints al reconstruir con código nuevo.

El procedimiento anterior se conserva en REPRODUCCION-v020-historical.md. Sus capturas e informes describen la entrega anterior, no el contrato vigente.

## Comprobaciones

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\r2.ps1 doctor
```

Las 21 pruebas finales originales se ejecutan contra el paquete instalado mediante un adaptador externo de importaciones. La suite añade regresión e integración. `audit/adquisition-final-baseline.json` identifica los archivos que deben permanecer intactos. Véase INTEGRACION_ADQUISITION.md para alcance y limitaciones.
