# odolab — sandbox de migracion Odoo (produccion inmutable + forks)

El experimento de recuperación de información de R2 se describe en
`r2/FUNCIONAMIENTO.md` y se ejecuta desde `../aws-lab/`. R2.1 termina en el
cruce inicial, después de adquisición, normalización y persistencia. R2.2
comprende relaciones, búsqueda, reporte, interfaz y evaluación.

Entorno reproducible para medir el desempeno de una herramienta propia de migracion
de modulos Odoo, contrastandola contra la migracion de referencia de la OCA
(**OpenUpgrade**), que se toma como correcta.

## Topologia

```
HOST (Docker Desktop)
└── sandbox  (proyecto compose "odolab", red aislada odolab-net)
    ├── sbx-db       Postgres 15      una instancia, varias DBs
    ├── sbx-prod     Odoo <version_inicio>   PRODUCCION — restart:unless-stopped, nunca se migra
    ├── sbx-control  CLI `odoolab`    orquesta todo (monta /var/run/docker.sock)
    └── sbx-fork-*   Odoo efimeros    uno por salto de version y por rama, se destruyen al terminar
```

`sbx-prod` solo se lee. Cada simulacion hace `CREATE DATABASE ... TEMPLATE prod`
(el "fork") y migra la copia. Antes y despues de cada run se toma una huella de
produccion y el run aborta si cambio.

## Puesta en marcha

```powershell
.\odoolab.ps1 up
```

```bash
./odoolab.sh up
```

Copia `.env.example` a `.env`, construye imagenes y levanta db + prod + control.
La primera vez tarda (descarga imagenes Odoo).

## Parametros de la simulacion

Los tres que pide el enunciado, por YAML o por linea de comandos:

```powershell
.\odoolab.ps1 run --name t1 --version-inicio 16.0 --version-fin 18.0 --modulos sale_management,stock,account
```

```powershell
.\odoolab.ps1 run scenarios/sample.yaml
```

| parametro | flag | YAML |
|---|---|---|
| version inicio | `--version-inicio` | `version_from` |
| version fin | `--version-fin` | `version_to` |
| modulos integrados | `--modulos` (csv) | `modules` |
| ramas a correr | `--arms ours,oca` | `arms` |
| invocacion de tu herramienta | — | `tool_cmd` |

`version_to` debe ser posterior a `version_from`; la migracion **encadena versiones**
(16.0 → 17.0 → 18.0), igual que lo haria el partner.

## Que hace un `run`

1. Siembra produccion con los modulos pedidos (si no existe).
2. Por cada rama (`ours`, `oca`) clona `prod` a `<name>_<arm>`.
3. Por cada salto de version levanta un fork con la imagen destino y:
   - **oca**: `git clone OCA/OpenUpgrade -b <ver>` (cacheado en volumen) y corre
     `odoo -u all --upgrade-path=openupgrade_scripts/scripts`.
   - **ours**: ejecuta `tool_cmd` dentro del fork y despues valida con `odoo -u all`.
4. Compara las dos bases resultantes.
5. Escribe `runs/<ts>-<name>/` con `report.md`, `report.json`, `comparison.json` y `logs/`.
6. Verifica que produccion sigue intacta y destruye los forks.

## Que compara

| dimension | criterio | severidad |
|---|---|---|
| esquema | columnas faltantes, tipos distintos, constraints, indices | error / warning |
| modulos | `ir_module_module.state` y version por modulo | error / warning |
| datos | conteo de filas por tabla y **hash md5 por registro** sobre columnas comunes | error |

Columnas y tablas de ruido (`write_date`, `ir_logging`, `bus_bus`, ...) se excluyen
via `compare.ignore_*` del escenario. La metrica principal es **fidelidad %** =
1 − divergencias criticas / objetos comparados.

## Reporte de esfuerzo

`report.md` seccion 3: modelo lineal de horas-persona sobre modulos, saltos de version,
errores de log, tracebacks, intervenciones manuales y divergencias contra OCA.
Los pesos estan en `control/odoolab/report.py:DEFAULT_WEIGHTS` — **calibralos con
datos reales de proyectos del partner antes de citar cifras en la tesis**; hoy son
supuestos explicitos, no mediciones.

## Comandos

```
odoolab status                 estado de contenedores y bases
odoolab init-prod <scenario>   siembra produccion (--force la recrea)
odoolab run ...                simulacion completa
odoolab compare <db_a> <db_b>  diff de dos bases ya migradas
odoolab clean [--all]          mata forks colgados (nunca toca produccion)
```

Desde dentro del sandbox es lo mismo:

```bash
docker exec -it sbx-control bash
odoolab status
```

## Tu herramienta

Se monta en `/opt/tool` (read-only) dentro de cada fork. Configura la ruta del host
en `.env` (`MIGRATION_TOOL_PATH`) y como se llama en `tool_cmd` del escenario:

```yaml
tool_cmd: "python3 {tool}/cli.py migrate --db {db} --from {src} --to {dst} --modules {modules}"
```

Placeholders: `{db} {src} {dst} {modules} {tool}`. Debe salir con codigo 0 y dejar la
base en un estado en que `odoo -u all` levante sin errores.

Los modulos custom del partner van en `custom-addons/` (se montan en `/mnt/extra-addons`).

## Limites conocidos

- El comparador solo mira Postgres; **no** compara filestore ni adjuntos binarios.
- El hash por registro se omite en tablas donde ya difiere el conteo (evita ruido).
- OpenUpgrade no cubre todos los modulos de todas las versiones: si un salto falla
  en la rama `oca`, la referencia para ese escenario no es valida y el reporte lo
  marca como `FALLO` en vez de inventar una fidelidad.
- El control usa el socket de Docker del host: quien entre a `sbx-control` puede
  controlar el Docker del host. Es un sandbox de laboratorio, no una frontera de seguridad.
