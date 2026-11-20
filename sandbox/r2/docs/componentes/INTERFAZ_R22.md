# Requisitos cumplidos: interfaz R2.2

## Propósito

Permitir que un partner use R2 sin construir manualmente URL, nombres técnicos o comandos extensos.

| ID | Requisito cumplido | Código principal |
|---|---|---|
| UI-01 | Exponer CLI instalable | `cli.py`, `pyproject.toml` |
| UI-02 | Ofrecer recorrido asistido `r2 start` | `assistant.start` |
| UI-03 | Detectar Odoo mediante `odoo-bin` y Git | `detect_odoo_checkout` |
| UI-04 | Descubrir addons por manifiesto | `discover_addons` |
| UI-05 | Elegir números, rangos, nombres o todos | `select_addons` |
| UI-06 | Mostrar versiones disponibles | `available_versions` |
| UI-07 | Resolver refs y generar diff local por SHA | `resolve_version_ref`, `local_diff` |
| UI-08 | Construir una colección y consultar varios addons | `run_local_analysis` |
| UI-09 | Guardar un reporte separado por addon | `_save_report` |
| UI-10 | Reutilizar rutas y versiones | `load_config`, `save_config` |
| UI-11 | Mantener comandos avanzados por etapa | `cli.parser` |
| UI-12 | Traducir errores previstos a mensajes de CLI | `cli.main` |

**Comandos:** `start`, `run`, `plan`, `query`/`search-units`, `build`, `capture-plan`, `delete-units`, `cross`, `extract-relations`, `export`, `validate-output`, `evaluate`.

**Límites:** interfaz de terminal, sin GUI ni dashboard; no ejecuta `git fetch`; el asistente local compara extremos directamente.

**Pruebas:** `test_assistant_r22.py`, `test_caja_negra.py`, pruebas CLI de componentes y suite integral.
