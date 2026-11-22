# Ejecución incremental y evaluación de R2

## Correr el lote en EC2

Usa un ID nuevo para esta versión. Si hay un lote activo, detén ese contenedor
con su propio ID antes de cambiar el código. Ejecuta desde la raíz del checkout
que contiene esta versión.

```bash
export R2_BATCH_ID=lote30_v7
bash aws-lab/run-30.sh start --next 1
bash aws-lab/run-30.sh logs
bash aws-lab/run-30.sh summary
```

Después del piloto, repite el siguiente bloque hasta cerrar los treinta casos.
`--next 5` toma los próximos casos pendientes o fallidos. Un reintento conserva
el intento anterior. `--only oca_v01_1617` permite seleccionar el piloto.

```bash
bash aws-lab/run-30.sh start --next 5
bash aws-lab/run-30.sh logs
bash aws-lab/run-30.sh summary
```

Cada caso analiza cinco addons en un salto. Graph y BM25 guardan las unidades
mostradas, sus localizadores y sus tiempos. `recommended-sources.json` reúne
hasta diez URL públicas distintas por motor y caso, intercalando puestos de los
cinco addons. La precisión se calcula sobre las unidades de cada consulta.
Los errores de adquisición y referencia quedan en `acquisition.json`,
`sources.log`, `execution.log` y `result.json`.

## Abrir los resultados por salto

En `aws-lab/results/$R2_BATCH_ID/logs/16.0-a-17.0/oca_v01_1617/README.md`
están los enlaces al intento, los logs y el dossier. Cada salto y caso tiene
su propio índice. El dossier reúne estos archivos.

| Archivo | Contenido |
| --- | --- |
| `primeras-unidades.csv` | Puesto, addon, motor, unidad, URL y vínculo al fragmento. |
| `nodos.csv` | Todos los nodos alcanzados, profundidad, aristas incidentes y enlace a la evidencia. |
| `addons/<addon>/graph/relations.json` | Extremos de cada arista, identidades compartidas, reglas y localizadores de ambos lados. |
| `unidades.html` | Fragmento normalizado, URL original y localizador por unidad del grafo o de la primera vista. |
| `mig-fix-candidatos.json` | URLs y SHA de commits candidatos recogidos en los repositorios de los cinco addons y del catálogo adicional. |
| `mig-fix-admitidos.json` | Referencias aprobadas y correcciones agrupadas después de `apply-review`. |
| `matriz-unidad-mig.csv` | Vínculos admitidos de C1 y cruce de unidades mostradas con las correcciones esperadas para C2. Incluye pertinencia, decisión de cobertura, motivo, URL y parche de referencia. |

El caso guarda los planes e inventarios bajo `adquisicion/`. Al terminar
el intento, el trabajador deja los resultados y el dossier; el controlador
retira la caché temporal, los checkouts, las descargas completas y la base de
trabajo. La revisión posterior usa los fragmentos normalizados y enlaces,
las copias de los parches de referencia y los rankings archivados. La
evaluación verifica los archivos y usa los tiempos del intento original.

## Emitir y aplicar los juicios

Cada intento genera el dossier `review/`. Su `REVIEW_PROMPT.md` y
`review-template.json` definen el formato. Los parches MIG y FIX se guardan
en `MIG/`, junto al código de los addons y las unidades completas del corpus.

`judge` se ejecuta en el host y usa por defecto una instalación autenticada de
Codex CLI. Lee el dossier en su directorio y guarda el JSON en
`aws-lab/results/$R2_BATCH_ID/reviews/`. Para usar otro asistente, pasa un
ejecutable disponible en el host con `--judge-command /ruta/al/asistente`.
El proceso recibe el prompt por stdin y devuelve un único objeto JSON por
stdout. Sus diagnósticos quedan en `judge.log` dentro del intento.

```bash
bash aws-lab/run-30.sh judge --only oca_v01_1617
bash aws-lab/run-30.sh apply-review --only oca_v01_1617
bash aws-lab/run-30.sh evaluate --only oca_v01_1617
```

El juicio documenta la capa técnica y el componente afectados. Para acreditar
cobertura vincula un cambio verificable de versión con la adaptación observada.
Por ejemplo, un diff del núcleo puede mostrar la retirada de un método que el
addon sobrescribía. El parche MIG documenta cómo el addon se adaptó, y el diff
del núcleo permite justificar el vínculo. Una alerta genérica o el nombre del
método por sí solo quedan como pistas para la revisión.
El importador exige los juicios de ambas vistas, los motivos y la incertidumbre.
Usa `judge --retry-judgments --only <caso>` para regenerar una respuesta
rechazada. Para revisar con un asistente fuera del host, empaqueta los casos
terminados con `review`, entrega el `review-bundle.tar.gz` generado y coloca la
respuesta de cada caso en `reviews/<case-id>.json`.

## Congelar la muestra y calcular las métricas finales

```bash
bash aws-lab/run-30.sh judge
bash aws-lab/run-30.sh apply-review
bash aws-lab/run-30.sh freeze-sample
bash aws-lab/run-30.sh evaluate --require-all --require-sample
bash aws-lab/run-30.sh summary
```

`freeze-sample` selecciona diez SHA MIG distintos por salto entre los admitidos,
en orden de SHA. Identifica los parches de referencia por repositorio y SHA, sus
correcciones, las consultas originales y las huellas de las revisiones en
`study-sample.json`. Si un salto tiene menos de diez MIG elegibles, informa
cuántos hay. Los FIX aportan correcciones de referencia y se cuentan por separado.
`--require-migs 30` sigue disponible como comprobación de cantidad total.

- **C1** mide qué proporción de las correcciones admitidas explica alguna unidad
  de la colección. Un commit queda cubierto si todas sus correcciones están
  cubiertas. Los estados parcial y sin cobertura se registran por separado.
- **C2** mide qué proporción de las correcciones esperadas explica la primera
  vista de cada motor. Cuenta cada corrección una vez cuando al menos una
  unidad mostrada es pertinente y tiene un vínculo validado con la corrección.
  También se registra la cobertura por MIG de la muestra.
- **P1(q)** es 100 × unidades pertinentes mostradas / unidades mostradas.
  Una vista vacía deja P1 indefinida. El resumen informa el número de consultas
  pareadas, la media por motor y la diferencia Graph − BM25. La meta se cumple
  cuando la diferencia es positiva.

`metrics.csv` y `evaluation.json` conservan los resultados del lote operativo.
En `summary.json`, `study_sample.metrics` recoge las métricas de la muestra
congelada y usa una sola vez cada consulta vinculada a sus MIG. Documenta
el alcance de la muestra y sus dependencias al presentar los resultados.

## Alcance de las referencias

El recolector busca commits `[MIG]` y `[FIX]` alcanzables desde el SHA destino
y ausentes del historial del SHA origen. Incluye todas las rutas de los
repositorios de los addons del caso. Admite asuntos que nombran el destino o
carecen de versión explícita. `--mig-catalog` agrega repositorios revisados
antes del primer bloque. Consulta
[`mig-sources.example.json`](mig-sources.example.json) para ver el formato.
Los PR sin fusionar quedan fuera de esta búsqueda Git.

Los candidatos se identifican antes de construir la colección para usar sus
SHA como criterio de exclusión. Los parches van al dossier de referencia.
El plan del lote rechaza PR y commits individuales, excluye los repositorios
de referencia de todos los casos y filtra los SHA conocidos de cada caso.
Los nombres de métodos, campos y vistas pueden coincidir con las referencias.
Los filtros identifican repositorios, addons y SHA conocidos; una copia
externa sin esos identificadores requiere revisión de procedencia.
