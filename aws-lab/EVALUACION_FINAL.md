# Ejecución incremental y evaluación final de R2

## Preparar una corrida nueva en EC2

Desde la raíz del checkout en Ubuntu, detén el contenedor de la corrida anterior
antes de actualizar. Si usabas el lanzador anterior a v5, ejecuta su comando
`stop` antes del `git pull`. No borres resultados anteriores ni la caché.

```bash
git pull --ff-only origin master
export R2_BATCH_ID=lote30_v5
bash aws-lab/run-30.sh start --next 1
bash aws-lab/run-30.sh logs
```

`logs` termina cuando el trabajador sale. `Ctrl+C` cierra solo la vista de logs.
Consulta el código de salida y los errores en `status`, `summary` y
`cases/<caso>/<intento>/execution.log`. Un fallo conserva su evidencia.

## Seguir por bloques

Cuando el primer caso termine, ejecuta los cinco siguientes:

```bash
bash aws-lab/run-30.sh start --next 5
bash aws-lab/run-30.sh logs
bash aws-lab/run-30.sh summary
```

Repite ese bloque hasta completar los treinta. `--next 5` selecciona hasta
cinco casos sin completar en el orden de `plan.json`, incluyendo reintentos
de fallos. Los completados se conservan. El bloque final puede contener menos
de cinco. Las treinta entradas operativas son grupos de cinco addons, no una
lista ya admitida de treinta commits MIG independientes. El objetivo académico
de treinta migraciones se comprueba con la selección de referencias revisadas.

También puedes repetir una selección fija:

```bash
bash aws-lab/run-30.sh start --offset 0 --count 5
bash aws-lab/run-30.sh start --offset 5 --count 5
# Ejecutar cada comando cuando haya terminado el anterior.
```

Mantén el mismo ID, código, catálogo y parámetros entre bloques. Con otro
código utiliza otro ID de lote. Las fuentes Git se fijan por SHA y la caché
de descargas se reutiliza. Una terminal nueva necesita volver a exportar
`R2_BATCH_ID=lote30_v5`.

## Obtener la evidencia para que el asistente emita los juicios

Después del primer caso, o después de cada bloque:

```bash
bash aws-lab/run-30.sh review
ls -lh "aws-lab/results/$R2_BATCH_ID/review-bundle.tar.gz"
```

El comando empaqueta los casos completados. Si hay casos intentados pero
incompletos informa de ellos y devuelve un código de error. Los demás dossiers
se conservan. Puedes seleccionar solo el piloto con `review --only oca_v01_1617`.

Descarga el archivo desde tu computadora con la misma clave SSH que ya funciona:

```powershell
scp -i "C:\ruta\tesis-odo.pem" ubuntu@44.205.67.137:/RUTA/AL/REPO/aws-lab/results/lote30_v5/review-bundle.tar.gz .
```

Sustituye la ruta remota por la que muestra `pwd` en la raíz del repositorio.
Entrega ese archivo al asistente para que emita los juicios reales. El dossier
incluye recomendaciones Graph/BM25, fragmentos completos, código del addon,
unidades no recuperadas y parches MIG. `REVIEW_PROMPT.md` contiene las reglas y
`review-template.json` el formato de respuesta. Se registra que el juicio lo
emitió un asistente, con motivos e incertidumbre; no se atribuye revisión humana
independiente. No se obtienen etiquetas de pertinencia solo por coincidencia léxica.

El asistente devolverá un JSON por caso, con nombre `<case-id>.json`. Copia
esos archivos a `aws-lab/results/lote30_v5/reviews/` en EC2. Por ejemplo:

```bash
mkdir -p "aws-lab/results/$R2_BATCH_ID/reviews"
```

Desde la computadora que tiene los juicios:

```powershell
scp -i "C:\ruta\tesis-odo.pem" .\reviews\*.json ubuntu@44.205.67.137:/RUTA/AL/REPO/aws-lab/results/lote30_v5/reviews/
```

## Aplicar juicios y calcular métricas

Para el primer caso:

```bash
bash aws-lab/run-30.sh apply-review --only oca_v01_1617
bash aws-lab/run-30.sh evaluate --only oca_v01_1617
```

Para todos los casos ya ejecutados:

```bash
bash aws-lab/run-30.sh apply-review
bash aws-lab/run-30.sh evaluate
bash aws-lab/run-30.sh summary
```

Al cerrar las treinta pruebas exige que ninguna esté sin ejecutar:

```bash
bash aws-lab/run-30.sh apply-review
bash aws-lab/run-30.sh evaluate --require-all --require-migs 30
bash aws-lab/run-30.sh summary
cat "aws-lab/results/$R2_BATCH_ID/summary.json"
```

`apply-review` rechaza juicios sin terminar, IDs desconocidos, evidencia alterada,
correspondencias con otro salto, hunks sin decisión y resultados sin juicio.
Los casos dudosos reciben una decisión y nota de incertidumbre. Las correcciones
sin evidencia permanecen en el denominador de cobertura. Si no hay correcciones
admitidas, el asistente debe explicarlo y la cobertura es indefinida.
`evaluate` devuelve error si falta revisión o un caso intentado está incompleto;
`--require-all` también exige los treinta casos del catálogo. `--require-migs 30`
exige al menos treinta commits MIG distintos admitidos: el resumen los lista
por repositorio, SHA y URL. El conteo de casos no sustituye ese conteo. Completar una
corrida operativa no certifica la independencia de la muestra académica.

## Archivos finales

- `metrics.csv`: P1, C2, C1, conteos y tiempos por addon y motor.
- `summary.json`: avance, C1 agregado y P1 medio de pares comparables.
- `cases.csv`: estado de todos los casos, incluidos fallos.
- `cases/<caso>/<intento>/evaluation.json`: métricas detalladas y denominadores.
- `evaluation-bars.txt` dentro del intento: barras de las métricas calculadas.
- `review/RECOMENDACIONES_MIG.md`: recomendaciones cruzadas con sugerencias MIG.
- `review/JUICIOS.md`, `review/review-applied.json` y `evaluation-spec.json`:
  decisiones, motivos, incertidumbre y vínculos admitidos.

La recolección automática consulta GitHub mediante Git y conserva todos los
commits `[MIG]` alcanzables en los repositorios OCA seleccionados para el destino,
incluyendo otros addons del repositorio. Conserva candidatos sin versión en el
asunto para su revisión. Los PR sin fusionar y otros repositorios están fuera
del alcance predeterminado. Amplía los repositorios antes de iniciar un lote con
`--mig-catalog /workspace/repo/aws-lab/mig-sources.json`, siguiendo el ejemplo
versionado. El catálogo adicional forma parte de la huella del protocolo.
