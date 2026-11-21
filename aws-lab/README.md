# Entorno de pruebas R2 en AWS Learner Lab

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
