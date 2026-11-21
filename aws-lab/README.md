# Entorno de pruebas R2 en AWS Learner Lab

## Lote R2 de treinta casos en EC2

Desde el checkout del repositorio en tu servidor Ubuntu, ejecuta:

```bash
git pull --ff-only origin master
export R2_BATCH_ID=lote30_v5
bash aws-lab/run-30.sh start --next 1
bash aws-lab/run-30.sh logs
```

Antes de actualizar un lote activo, detén su contenedor con
`bash aws-lab/run-30.sh stop`. Los cambios de algoritmo o de adquisición exigen
una corrida con un nuevo `R2_BATCH_ID`. Los trabajadores comprueban la huella
del código y del plan para conservar las condiciones de cada corrida.

El proceso corre en un contenedor en segundo plano y continúa al desconectar
SSH. `Ctrl+C` en la vista de logs cierra esa vista. Para detener el cálculo usa
`bash aws-lab/run-30.sh stop`. Con `start` se reanuda el lote. Si falta Docker,
el lanzador lo instala mediante el bootstrap de esta carpeta con `sudo`.
`start` sin argumentos ejecuta el siguiente caso. Al terminar, repite
`start --next 5` para ejecutar los cinco siguientes; los casos completados se
omiten y los parciales se reintentan. `--offset 5 --count 5` selecciona las
posiciones 6 a 10 del catálogo; `--only oca_v01_1617` permite elegir un caso.
La selección del bloque no cambia el protocolo ni exige otro ID de lote.
No actualices el código entre bloques de una misma corrida.

El procedimiento de revisión y los comandos finales están en
[EVALUACION_FINAL.md](EVALUACION_FINAL.md).

El lote toma los treinta grupos nuevos de
`sandbox/research/migration-plan/plan.json`, cinco addons en cada grupo, para
los saltos 16→17, 17→18 y 18→19. Primero fija las revisiones del núcleo de
Odoo. Luego prepara los snapshots de OCA y comprueba los manifiestos en origen
y destino. Los repositorios locales se reutilizan cuando están disponibles.
Los cinco addons se inspeccionan conjuntamente para delimitar el diff local
del núcleo por salto mediante `git diff`. Después se ejecutan planificación y adquisición web
para complementar el diff con guías, documentación, snapshots y URL técnicas
admitidas por el catálogo. Los inventarios se fusionan antes de normalizar.
R2.1 termina con el cruce inicial, conservado por addon y agregado para el
grupo. R2.2 extrae relaciones, busca, ordena y emite reportes por addon.

El lote compara exclusivamente Graph y BM25 por unidades. Cada consulta presenta hasta
diez resultados y se repite tres veces alternando el orden de los motores.
El total previsto es de 150 consultas de addons y 900 ejecuciones de motor
durante la medición inicial; la evaluación vuelve a consultar para verificar
las entradas y medir sus tiempos.
`logs` muestra, al terminar cada caso, los candidatos a revisar del grafo por
addon, con su título e ID. El reporte detallado se guarda en el intento.
El PostgreSQL y los forks del sandbox de migración se ejecutan mediante la
CLI `odoolab` documentada más abajo. Este lote mide el análisis estático de R2.

Los casos se procesan en serie. Cada caso usa un proceso propio para liberar
memoria al terminar. Los errores de fuentes y addons quedan registrados y el
lote continúa con los demás casos. Un caso parcialmente completado conserva
su intento original y se vuelve a ejecutar en un intento nuevo. Los casos
completados se reutilizan después de verificar sus hashes. Los bloqueos se
liberan al detenerse el proceso. Los SHA quedan fijados durante toda la corrida.

```bash
bash aws-lab/run-30.sh status
bash aws-lab/run-30.sh summary
```

Las salidas están en `aws-lab/results/$R2_BATCH_ID/`:

- `manifest.json` fija parámetros, versiones y hashes del código.
- `sources.json` conserva los SHA de las fuentes.
- `summary.json`, `cases.csv` y `metrics.csv` muestran el avance y los conteos.
- `cases/<caso>/latest.json` señala el intento actual y su estado.
- Cada intento guarda `execution.log`, `sources.log`, la colección SQLite,
  inventario, bindings, alcance del diff y la procedencia de cada addon.
- `initial-crossing.json` y `r21-crossing/` conservan el cierre de R2.1 antes
  de las consultas relacionales.
- `acquisition/` conserva planificación, capturas originales, inventario
  fusionado y colección complementada. Los estados de captura permanecen
  visibles en `acquisition.json`, también ante una fuente fallida.
- `addons/<addon>/graph/` y `bm25/` conservan resultados
  estructurados. Cada addon tiene tiempos por repetición, hashes,
  y `judgments.csv` por unidad.
- `references/pool/` conserva los commits candidatos `[MIG]` y sus parches
  para la revisión externa de correcciones después de ejecutar las consultas.
  Se busca el historial de los repositorios OCA de los cinco addons completos,
  incluyendo MIG de otros addons. `--mig-catalog` permite agregar repositorios
  OCA revisados (formato en `mig-sources.example.json`). El alcance queda fijado
  por SHA, con errores y limitaciones explícitos; no se afirma una búsqueda
  exhaustiva de todo Internet. Se admiten correcciones después del juicio técnico.
  `references/<addon>/suggested-links.json` vincula cada hunk con unidades del salto,
  resultados recuperados y sus fuentes cuando comparten identificadores
  cualificados o con guion bajo. Los logs muestran cuántos hunks tienen
  sugerencias. El archivo conserva también hunks sin vínculos y avisos.
  La colección usa el diff del núcleo y las fuentes web admitidas. Los parches
  de solución de los addons evaluados se conservan en el dossier de referencia.
- `review/RECOMENDACIONES_MIG.md` muestra las recomendaciones de ambos motores
  cruzadas con los hunks sugeridos. `packet.json`, `corpus-units.json`,
  `addon-sources.json` y `MIG/` conservan la evidencia para emitir el juicio.
  Se incluye la colección completa para detectar correcciones no recuperadas.

El catálogo operativo contiene treinta grupos de laboratorio. El objetivo
académico del autor son treinta migraciones de referencia: los MIG admitidos
deben identificarse y documentarse; treinta grupos no acreditan treinta MIG
independientes. Se comienza por un caso. El autor encarga al asistente los
juicios finales, registrados como revisión asistida por IA. Hasta disponer
de esa revisión, C1, P1 y C2 aparecen pendientes. Los errores, vistas vacías
y denominadores se conservan.

Para calcular las métricas, genera el dossier con `review` y devuelve los
juicios del asistente en `reviews/<case-id>.json`, según `review-template.json`
y `REVIEW_PROMPT.md`. `apply-review` valida su integridad y completa
`evaluation-spec.json` de cada intento.
El archivo trae la revisión de colección, rutas, saltos y consultas fijados.
Completa `reviewer`, las `references` con correcciones evaluables y
`available_unit_ids`, y para cada consulta sus `reference_ids` y `judgments`
revisados (`relevant` y `reference_ids` por unidad). Usa `judgments.csv` y los
dossiers como instrumentos de revisión. Confirma las sugerencias de
`suggested-links.json` y agrega relaciones que la coincidencia léxica haya
omitido. Un hallazgo puede ser útil aunque
carezca de correspondencia con una corrección del MIG.

```bash
bash aws-lab/run-30.sh evaluate
```

El evaluador vigente de R2 verifica los juicios y produce `evaluation.json`,
`evaluation-bars.txt` y `evaluation-status.json` por caso. Se actualizan los
CSV y el resumen con las cifras disponibles y el número de pares comparables.
C1 se agrega mediante los conteos de correcciones cubiertas y evaluables;
P1 usa la media de pares Graph/BM25 con precisión definida. Una especificación
editada exige volver a evaluar antes de incorporar sus cifras al resumen.

`r2 evaluate` y `evaluation.json` conservan exclusivamente la comparación por
unidades del protocolo acordado. Las funciones históricas de fuentes completas
permanecen para lectura de ensayos anteriores y no se ejecutan en el lote nuevo.

`timing.json` distingue consulta completa y etapas. Cada tiempo se toma de
forma síncrona en el trabajador. El contenedor del lote corre en segundo
plano. `relations_seconds` mide extracción, recorrido y validación de
relaciones. `bm25_units_seconds` mide la búsqueda léxica por unidades. La
preparación de fuentes y de índices queda registrada aparte de esos tiempos.

El catálogo predeterminado está en
`sandbox/r2/reference/adquisition-final/examples/catalog.json`. La adquisición
propone fuentes técnicas a partir de los addons y agrega las URL revisadas
que figuren en `allowed_urls`. Los PR y diffs específicos adicionales necesitan
sus URL y bindings revisados en el catálogo. Se omite el compare global del
núcleo, cubierto por el diff local filtrado. Las soluciones de evaluación y
los identificadores excluidos conservan la política de admisión vigente.

Para una corrida nueva tras cambiar el código o el plan, usa un identificador:

```bash
R2_BATCH_ID=lote30_v5 bash aws-lab/run-30.sh start --next 1
R2_BATCH_ID=lote30_v5 bash aws-lab/run-30.sh logs
```

Conserva el mismo identificador para los comandos de esa corrida. Los
directorios de resultados y caché persisten en el disco de EC2.

## Asistente Python desde tu computadora

Copia `.env.example` a `.env` en esta carpeta y completa las tres credenciales
temporales de AWS Details. También admite pegar el bloque AWS CLI con
`[default]` y nombres en minúscula. Ejecuta el asistente desde tu computadora,
con Python, AWS CLI v2, Git y OpenSSH disponibles. El asistente y su entorno
Python se encuentran dentro de `aws-lab/`.

```powershell
cd aws-lab
.\.venv\Scripts\python.exe iniciar.py
```

Para preparar ese entorno por primera vez desde `aws-lab`, ejecuta
`python -m venv .venv`. Todos los scripts de aprovisionamiento utilizan la
biblioteca estándar de Python. En Linux usa `python3 iniciar.py` desde esta
carpeta. También puedes ejecutar `python iniciar.py` con tu Python local. `--env`
permite indicar otra ruta de credenciales. `--plan` comprueba identidad, red y
parámetros antes de crear recursos.

El asistente valida el acceso, selecciona una subred con ruta pública,
detecta tu IPv4 pública para restringir SSH, genera e importa un par SSH,
crea EC2, espera la conexión, sube este repositorio y prepara Docker, Odoo,
PostgreSQL y R2. La ejecución normal crea recursos que consumen el saldo del
laboratorio. Si usas la clave del curso, completa juntos `EC2_KEY_PAIR` y
`SSH_KEY_PATH`. Conserva `.state/asistente/` para reutilizar la instancia y su
clave al repetir el comando tras un fallo. La fase de sincronización reutiliza
los volúmenes de datos del servidor.

Las credenciales permanecen en el archivo local y en el entorno del proceso.
La sincronización excluye `.env` y `.state/`. Las claves caducadas, restricciones
de IAM o una cuenta que siga en cleanup se informan con el error de AWS. El
asistente necesita las credenciales vigentes del laboratorio para avanzar.

## Componentes del entorno

Esta carpeta crea un host Ubuntu 24.04 x86_64 y prepara PostgreSQL 15, Odoo y R2
en contenedores contiguos. El directorio del repositorio se monta en R2 para
ejecutar el código de trabajo. El análisis estático recibe un checkout Git del
núcleo y los addons mediante `/data`. Las salidas persistentes van a `results/`.

La configuración inicial usa `m5.xlarge`, 4 vCPU y 16 GiB, con 100 GiB gp3
cifrados. El parámetro `--instance-type` permite elegir otro tipo admitido por
tu Learner Lab. Las políticas de cada curso determinan los tipos y límites
disponibles. Una denegación de AWS queda visible en la CLI.

## Crear el servidor

Primero verifica qué identidad usa tu terminal. El terminal del Learner Lab
puede arrancar con el rol de infraestructura `runserver`. En la sesión reportada
ese rol carece de `ec2:DescribeSubnets`. La guía anterior presuponía que la
terminal ya usaba las credenciales temporales de tu laboratorio.

Abre **AWS Details** en el laboratorio activo y busca las credenciales **AWS
CLI**. Usa los tres valores de esa sesión, access key, secret key y session
token. Desde la raíz del repo puedes cargarlos mediante preguntas ocultas.

```bash
source aws-lab/use-lab-credentials.sh
python3 aws-lab/ec2.py doctor --region us-east-1
```

El script valida los valores con STS y los exporta a la sesión actual. Las
variables de entorno tienen precedencia sobre las credenciales de instancia.
Si el laboratorio reinicia o las credenciales expiran, repite este paso con los
valores vigentes. Con una identidad del laboratorio que siga recibiendo una
denegación, el administrador del curso debe revisar sus permisos de EC2. El
diagnóstico conserva el error concreto de AWS y detiene el aprovisionamiento.
Si el panel no ofrece credenciales CLI, usa el enlace AWS del laboratorio para
comprobar el acceso a EC2 en la consola y consulta al instructor por acceso CLI.

Cuando `doctor` muestre subredes y claves disponibles, usa esos identificadores
para preparar el plan. Los ejemplos usan
`python3`, equivalente al Python del entorno virtual en Windows.

```bash
python3 aws-lab/ec2.py launch --subnet subnet-REEMPLAZAR \
  --key-pair vockey --ssh-cidr TU_IP_PUBLICA/32
```

El primer comando `launch` imprime el plan. Repite sus parámetros con `--apply`
para crear la instancia y el disco, que consumen el saldo del laboratorio.
Elige una subred con ruta a Internet para las descargas y el acceso SSH. Usa
una clave existente cuya parte privada tengas disponible. `--security-group`
permite reutilizar un grupo con SSH habilitado. Si omites ese argumento, el
programa crea un grupo que permite el puerto 22 desde el CIDR indicado.
`--profile LabInstanceProfile` es opcional cuando el laboratorio lo exige.
`--ami` permite indicar una imagen Ubuntu 24.04 amd64 verificada en tu región.

El estado de aprovisionamiento queda en `.state/instance.json`. Los reintentos
con los mismos parámetros reutilizan el identificador de idempotencia y el
grupo creado. Un archivo `.lock` evita dos creaciones concurrentes. Si un
proceso fue terminado abruptamente, revisa primero el estado en EC2 y elimina
ese lock para reanudar. Conserva el estado mientras exista la instancia.

```bash
python3 aws-lab/ec2.py status
python3 aws-lab/ec2.py stop
python3 aws-lab/ec2.py start
```

`status` muestra el estado, DNS e IP pública. La IP puede cambiar al reiniciar.
Parar la instancia conserva el disco y su costo de almacenamiento. Elimina los
recursos desde la consola cuando hayas respaldado los resultados y terminado
el proyecto. Los archivos de estado y las claves permanecen excluidos de Git.

## Enviar este código y preparar Docker

Ejecuta desde tu máquina local, que contiene esta versión del repositorio y la
clave SSH del laboratorio. `sync.py` transmite los archivos versionados tal
como están en el árbol de trabajo, los archivos nuevos de R2 admitidos por Git
y los scripts de esta carpeta. Así incorpora
los cambios de CLI que aún no hayan llegado al remoto. La carpeta `data/` se
transfiere aparte y conserva tus clones y addons entre actualizaciones.

```bash
python3 aws-lab/sync.py --host IP_PUBLICA_EC2 --key /ruta/labsuser.pem
ssh -i /ruta/labsuser.pem -L 8069:127.0.0.1:8069 ubuntu@IP_PUBLICA_EC2
```

El bootstrap instala Docker y Compose. La sincronización espera que termine,
extrae el repo en `/opt/tesis/repo` y ejecuta `setup.sh`. El script genera una
contraseña de PostgreSQL y levanta Odoo 16 y PostgreSQL con volúmenes
persistentes. Construye R2 sobre Python 3.12. Los registros del bootstrap están
en `/var/log/tesis-bootstrap.log`. Odoo se consulta mediante el túnel SSH en
`http://localhost:8069`. El puerto de PostgreSQL queda en la red Docker.

En EC2 comprueba el entorno y ejecuta el laboratorio de R2.

```bash
cd /opt/tesis/repo
bash aws-lab/r2.sh --version
docker compose --env-file aws-lab/.env -f aws-lab/compose.yml run --rm \
  --entrypoint python r2 -m unittest discover -s tests -v

git clone --filter=blob:none --branch 16.0 https://github.com/odoo/odoo.git aws-lab/data/odoo
git -C aws-lab/data/odoo fetch origin 17.0:refs/heads/17.0
```

Coloca los addons de origen en `aws-lab/data/addons/` mediante Git o SCP.
Para los saltos 17→18 y 18→19, incorpora sus refs locales y los addons de la
versión de origen. R2 usa los SHA de las referencias locales. Conservarlos en
el manifiesto permite repetir las mediciones aunque cambien las ramas.

```bash
bash aws-lab/r2.sh start --odoo /data/odoo --addons /data/addons \
  --from 16.0 --to 17.0 --select all --config /data/r2-config.json \
  --output-dir /results/piloto-1617

bash aws-lab/r2.sh charts /results/piloto-1617/addons/NOMBRE_ADDON --top 10
bash aws-lab/r2.sh charts /results/piloto-1617/addons/NOMBRE_ADDON --level 1
bash aws-lab/r2.sh query /data/addons/NOMBRE_ADDON --db /results/piloto-1617/collection.sqlite \
  --module-name NOMBRE_ADDON --from 16.0 --to 17.0 --format bars

bash aws-lab/r2.sh evaluate /data/evaluacion-revisada.json \
  --db /results/piloto-1617/collection.sqlite --repeats 3 > aws-lab/results/evaluacion.json
bash aws-lab/r2.sh charts /results/evaluacion.json --ascii
```

La especificación de evaluación conserva referencias y juicios revisados según
la tesis. `charts` grafica P1 y C2 disponibles y muestra C1 y los valores
indefinidos. Las barras estructurales describen el cruce y los caminos del grafo.
Cada nodo cuenta evidencias directas más incidencias de coincidencias en sus
aristas. Cada atributo usa la identidad completa con su tipo y ámbito. Una
arista cuenta cuántos caminos mínimos hacia los niveles elegidos la contienen,
incluyendo empates. `--level` filtra los destinos de esos caminos. El gráfico
por nivel resume todos los nodos del grafo extraído antes de los filtros finales
del reporte. `--format json` exporta IDs completos y conteos.

Para ejecutar el sandbox completo de migraciones con forks, sigue su CLI
existente desde `sandbox/`. Antes detén `odoo` del entorno de esta carpeta para
liberar el puerto 8069. El sandbox tiene su PostgreSQL, volúmenes y controlador.

```bash
docker compose --env-file aws-lab/.env -f aws-lab/compose.yml stop odoo
cd sandbox
bash odoolab.sh up
bash odoolab.sh plan list
bash odoolab.sh plan check
```

El plan conserva las validaciones de fuentes y dependencias de cada caso.
Ejecuta migraciones en serie para conservar comparabilidad. Guarda SHA,
configuración y estado de caché en cada corrida. Para descargar los resultados
del entorno R2 usa `scp -r ubuntu@IP:/opt/tesis/repo/aws-lab/results ./resultados-aws`
con la misma clave SSH.

Referencias de infraestructura

- https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html
- https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_use-resources.html
- https://docs.aws.amazon.com/cli/latest/reference/ec2/run-instances.html
- https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/user-data.html
- https://aws.amazon.com/ec2/instance-types/m5/
