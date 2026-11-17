# R2 Información local de migración de Odoo 0.3

Aplicación determinista en Python 3.12 para consultar cambios de Odoo. No usa IA ni embeddings. La integración final conserva intacto el componente del usuario en `r2/adquisition`.

## Componentes

- `r2/adquisition`: componente final de descarga y eliminación; no se modificó.
- `r2/ingestion`: lectura offline de unidades aceptadas y bindings de versiones.
- `r2/conversion`: interpretación de diffs, PR JSON, manifiestos y documentos.
- `r2/collection.py`: persistencia SQLite; esquema 3 para el flujo actual.
- `r2/extract.py`, `graph.py`, `query.py`: extracción estática, cruce, BFS con NetworkX, filtro y ordenamiento; BM25 como referencia.
- `r2/evaluation_sources`: cliente independiente de metadatos para selección, sin soluciones.
- `r2/evaluate.py`: evaluación con juicios externos; sus fixtures no son resultados académicos.

El flujo actual es plan + catálogo → adquisición → inventario de sesión → ingestión/conversión → SQLite → consulta. Documentos y comentarios aportan contexto; solo los diffs producen candidatos. Los hunks son parciales y no acreditan reconstrucción de archivos completos.

## Empezar

```powershell
.\r2.ps1 --help
.\.venv\Scripts\python.exe -m examples.run_session_demo --output examples/output/v030-session
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

La demostración es sintética y offline. No realiza descargas de producción ni una migración. El directorio de salida debe ser nuevo.

Para capturas reales se necesita revisar y completar el catálogo: el de referencia tiene `allowed_urls` vacío. Se mantiene la política fija final, sin interruptor de inclusión OCA. No se afirma ausencia absoluta de filtraciones.

## Documentación vigente

- [Integración y contratos](docs/INTEGRACION_ADQUISITION.md).
- [Reproducción y comandos](docs/REPRODUCCION.md).
- [Manual de codificación](docs/MANUAL_CODIFICACION.md).
- [Protocolo académico](docs/PROTOCOLO_EVALUACION.md).
- [Pendientes](PENDIENTES.md).
- [Informe de integración y pruebas](audit/INTEGRACION_030.md).

`reference/adquisition-final` conserva la entrega original con investigación y pruebas; ese material no se indexa automáticamente. `archive` conserva la implementación anterior. Las bases de esquema 2 se consultan sin reescribirlas; `build-legacy` identifica su reconstrucción local histórica y no equivale a admisión mediante el catálogo final.

La evaluación independiente, catálogo completo, revisores y decisiones académicas siguen pendientes. Las nuevas colecciones no se marcan automáticamente como académicamente auditadas. Los informes previos de `audit` y sus hashes identifican entregas históricas; el Word de la tesis no se modifica.


## Prueba funcional con entrada OCA

La prueba con sale_advance_payment 16.0.1.0.0 se reproduce con `.venv\Scripts\python.exe -m examples.run_oca_functional_test --output examples/output/oca-functional-otra-ejecucion`. Usa código local real y HTTP/revisión simulados; no ejecuta una migración. Véase [resultado y límites](audit/OCA_FUNCIONAL_16_17.md).
