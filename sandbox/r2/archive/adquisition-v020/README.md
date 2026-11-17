# Recolección de fuentes desde internet

Este paquete implementa la recolección HTTP y la consulta de metadatos de GitHub. Se conserva el nombre `adquisition` solicitado para el módulo.

| Archivo | Responsabilidad |
|---|---|
| `http.py` | Transporte HTTPS, redirecciones, reintentos, captura de respuestas y diagnóstico de errores. |
| `sources.py` | Ejecución de planes de fuentes generales, estados antes/después, inventario y reporte de captura. |
| `github.py` | Consultas REST, paginación y proyección de metadatos de PR, revisiones y archivos. |
| `provenance.py` | Fechas UTC, hashes SHA256, validación de origen y escritura de registros JSON. |
| `__init__.py` | Entradas públicas: `HttpCapture`, `GitHubMetadata` y `capture_plan`. |

La conversión de texto está en `r2/normalization.py`. `sources.py` la invoca para preparar la copia textual; la implementación de conversión no pertenece al transporte. La captura conserva también los bytes originales y hashes separados.

La lectura local de Git y snapshots permanece en `collection.read_source()`. La construcción SQLite, extracción, consulta y evaluación continúan en sus módulos correspondientes. Este paquete no importa esas etapas ni ejecuta el código descargado.

La CLI usa directamente este paquete para `capture-plan` y `github`. Los scripts de auditoría también usan las rutas nuevas. `r2/acquire.py` conserva únicamente reexportaciones de compatibilidad para consumidores anteriores; no duplica implementaciones.

Se mantienen los formatos de captura, inventario y errores, los comandos y las políticas existentes. La refactorización no amplía el corpus ni completa la selección o evaluación académica pendiente.

Verificación desde la raíz del proyecto: `.venv\Scripts\python.exe -m unittest discover -s tests -v`. Las pruebas HTTP usan respuestas simuladas; no requieren internet. La prueba de integración captura mediante la CLI, construye una colección offline y rechaza una captura original alterada.
