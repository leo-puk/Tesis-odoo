# Catalogo de 32 casos

Se conservan los grupos historicos `g01` y `g02`, ambos 16.0→17.0. Se agregan diez variantes, cada una con cinco addons fijos y tres saltos consecutivos. Los pilotos `sale_advance_payment` y `sap_guiado` siguen existiendo; no cuentan entre los 32 casos.

| Clase | Codigo | Casos |
|---|---|---:|
| Historicos | `g01`, `g02` | 2 |
| Nuevos, 16→17 | `oca_v01_1617` … `oca_v10_1617` | 10 |
| Nuevos, 17→18 | `oca_v01_1718` … `oca_v10_1718` | 10 |
| Nuevos, 18→19 | `oca_v01_1819` … `oca_v10_1819` | 10 |

`plan.json` es la fuente unica de identidades, versiones, repositorios y addons. No se copian sus entradas a `meta.json` hasta preparar el caso. Los resultados y validaciones se guardan en archivos separados; el programa no reemplaza addons automaticamente ni altera las definiciones para hacer pasar una prueba.

La variante `oca_v01` usa `stock_picking_filter_lot` en lugar de `stock_picking_auto_create_package`. El segundo no existe en la rama OCA 16.0 verificada. Se comprobaron los manifiestos instalables del reemplazo en los refs OCA 16.0 (`6cef26ac`), 17.0 (`faf6f074`), 18.0 (`0d3301f7`) y 19.0 (`80d754ec`); todos dependen de `stock`. El censo registra la migracion 16.0→17.0. La validacion completa de dependencias y ejecucion para 17.0→18.0 y 18.0→19.0 sigue pendiente. Los resultados de las pruebas parciales anteriores corresponden a la seleccion antigua.

La seleccion conserva la propuesta aleatoria con semilla 20261120. Los 50 addons nuevos no repiten los diez addons de g01/g02. Los nombres aparecen en los catalogos de 18/19 consultados al elaborar la propuesta; continuidad 16/17, dependencias, instalacion y exclusion de OWL siguen pendientes. Tener un caso en este catalogo no implica que ya haya sido validado ni ejecutado.

## Uso

Desde `sandbox`, usando el contenedor de control existente:

```powershell
.\odoolab.ps1 plan list
.\odoolab.ps1 plan check
.\odoolab.ps1 plan check --verify-sources --only oca_v01_1617
.\odoolab.ps1 plan prepare --only oca_v01_1617
.\odoolab.ps1 plan run --only oca_v01_1617
.\odoolab.ps1 plan summary
```

Tambien funciona sin Typer/Rich/PyYAML, con Python 3.12 y el paquete de control en PYTHONPATH:

```powershell
$env:PYTHONPATH = 'control'
python -m odoolab.migration_plan check
```

`plan check` valida la estructura local y no usa Docker, red ni modifica experimentos. `--verify-sources` lee los censos, consulta clones OCA y verifica los commits MIG y dependencias; escribe `source-validation.json`. Puede actualizar caches Git, pero no crea bases ni reconstruye experimentos.

Antes de verificar los saltos se necesitan los censos `modules_170.csv`, `modules_180.csv`, `modules_190.csv` y los inventarios `core_addons_160.txt`, `core_addons_170.txt`, `core_addons_180.txt`, `core_addons_190.txt` en `research/census`. Se producen con la herramienta de censo existente; no se inventan archivos vacios para omitir comprobaciones.

`plan prepare` exige un unico caso. Valida fuentes antes de escribir y reutiliza metadatos existentes solo si sus addons y salto coinciden. `--force` permite reconstruir explicitamente ese caso y borrar su evidencia operativa; nunca se usa implicitamente. Si falta un addon, un MIG separable o una dependencia, el caso se bloquea y muestra el motivo. No se sustituyen nombres.

`plan run` sin `--only` selecciona los treinta nuevos y no vuelve a ejecutar g01/g02. Se ejecuta en serie; cada salto obtiene sus versiones desde los metadatos del caso. Cada fase fallida produce estado `failed`, y un error de preparacion produce `blocked`. Ambos hacen que la orden termine con codigo distinto de cero. `execution-status.json` registra la ultima ejecucion por caso. No se considera aprobado un caso porque el orquestador simplemente haya terminado.

El comando anterior `lote run` sigue atendiendo las muestras antiguas. Para el catalogo nuevo puede usarse con `--parallel 1`; el formato se detecta por `schema`. `lote summary` tambien reconoce este catalogo.

## Compatibilidad y limites

- Los valores predeterminados de `exp prepare` siguen siendo 16.0→17.0; se agregan `--version-inicio` y `--version-fin`.
- `seed`, `baseline`, `run`, aplicacion de hunks y registro de casuisticas obtienen versiones por caso. No se cambian globales compartidas para ejecutar un salto distinto.
- Las dependencias se recorren en origen y destino antes de recrear directorios; se rechazan nombres ambiguos y dependencias externas sin revision. La validacion es conservadora: exige continuidad de las dependencias en ambas versiones.
- Se mantienen los campos historicos `sha16`/`sha17` y `rev16` para los casos correspondientes. Los nuevos usan tambien campos explicitos de origen/destino.
- Las reglas de guia G17 solo se aplican al destino 17.0. Para 18/19 la guia queda `pending`, los hunks se etiquetan `GUIA_PENDIENTE` y la cobertura inferida queda `?`. No se presenta una regla de 17 como evidencia de cobertura en 18/19.
- Cada salto es un experimento independiente con los mismos cinco addons. Este cambio no encadena una misma base de datos desde 16 hasta 19. Las dependencias pueden aumentar el total instalado.
- No se editan las exclusiones de R2, los pilotos ni los resultados historicos. Registrar un caso no lo incorpora automaticamente al conjunto independiente de validacion de R2.
- No se certifica instalacion ni compatibilidad completa por tener manifiesto o catalogo. Las imagenes Odoo, PostgreSQL, OpenUpgrade y las pruebas reales deben verificarse en el entorno Docker.

## Verificacion del cambio

Desde la raiz del repositorio, con Python 3.12:

```powershell
python -m unittest discover -s sandbox/tests -v
```

Las pruebas cubren las 32 identidades, los mismos addons en los tres saltos, los diez historicos originales, lectura simultanea de versiones sin cambiar globales, dependencias de origen/destino, proteccion de evidencia existente, rechazo de casos invalidos y errores de fase. No ejecutan Odoo, Docker ni llamadas a GitHub.
