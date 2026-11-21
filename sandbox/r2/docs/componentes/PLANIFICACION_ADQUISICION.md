# Requisitos cumplidos: planificación y adquisición

## Propósito

Este componente pertenece a R2.1. Sus capturas alimentan normalización,
persistencia y cruce inicial. En el experimento de AWS se ejecuta después de
obtener el diff local filtrado y complementa esa fuente con documentación,
guías y otras URL admitidas por el catálogo.

Preparar y capturar fuentes completas con procedencia explícita, sin decidir todavía su relevancia para un addon.

| ID | Requisito cumplido | Código principal |
|---|---|---|
| PA-01 | Validar versiones ascendentes y dividir intervalos web en saltos adyacentes | `planner.version_pairs` |
| PA-02 | Inspeccionar código y URL sin ejecutar el addon | `planner.repository_links`, `crossing.code.read_code` |
| PA-03 | Detectar dependencias, XML IDs e importaciones explícitas | `planner.input_scope` |
| PA-04 | Generar plan, catálogo, bindings y diagnóstico | `planner.make_plan`, `planner.write_plan` |
| PA-05 | Exigir catálogo, IDs simples, tipos conocidos y archivos planos | `sources.capture_plan` |
| PA-06 | Validar todas las URL antes de solicitar una unidad | `capture_plan` |
| PA-07 | Cubrir código/manifiestos, documentación, guía OCA, OpenUpgrade, diff y PR | `capture_plan`, `validate_source_origin` |
| PA-08 | Conservar bytes y metadatos de decodificación | `capture_plan`, `documents` |
| PA-09 | Registrar accepted, excluded, quarantined, incomplete, failed y deleted | `inventory.json`, `acquisition.jsonl` |
| PA-10 | Reintentar fallos transitorios y continuar el lote | `http.py`, `github.py` |
| PA-11 | Restringir almacenamiento y rechazar enlaces de archivos | `_root` y validaciones de rutas |
| PA-12 | Eliminar unidades sin afectar otras | `delete_units` |

**Entrada:** addon/repositorio, versiones, catálogo y plan opcional.  
**Salida:** `plan.json`, `catalog.json`, `bindings.json`, `planning.json`, originales e inventario.

**Límites:** el planner propone candidatos, Acquisition no calcula relaciones y las fuentes web dependen de red. Los binarios no inspeccionables no se admiten como texto.

**Pruebas:** `test_planner.py`, `test_acquisition_originals.py`, `test_final_adquisition.py` y pruebas de sesión.
