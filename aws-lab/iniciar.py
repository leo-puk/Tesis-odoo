"""Run locally to provision EC2 and install the R2 Docker environment from a .env file."""
import argparse
from contextlib import redirect_stdout
import io
import ipaddress
import json
import os
from pathlib import Path
import shutil
import subprocess
import time
from urllib.request import urlopen
import uuid

import ec2
import sync

ROOT = Path(__file__).resolve().parent
CREDENTIALS = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN")
CONFIGURATION = {"AWS_DEFAULT_REGION", "EC2_INSTANCE_TYPE", "EC2_DISK_GIB", "EC2_KEY_PAIR", "SSH_KEY_PATH",
                 "EC2_SUBNET_ID", "SSH_CIDR", "EC2_SECURITY_GROUP", "EC2_AMI", "EC2_PROFILE"}


def load_environment(path):
    values = {}
    for number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith(("#", "[")):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        key, separator, value = line.partition("=")
        if not separator:
            raise ValueError(f"Revisa la línea {number} del .env. Usa NOMBRE=valor.")
        key = key.strip().upper()
        if key not in CONFIGURATION | set(CREDENTIALS):
            continue
        value = value.strip()
        if value.startswith(("'", '"')):
            if len(value) < 2 or value[-1] != value[0]:
                raise ValueError(f"Comillas incompletas en la línea {number} del .env.")
            value = value[1:-1]
        else:
            value = value.split(" #", 1)[0].strip()
        values[key] = value
    missing = [key for key in CREDENTIALS if not values.get(key)]
    if missing:
        raise ValueError("Completa estas entradas en el .env: " + ", ".join(missing))
    os.environ.update({key: values[key] for key in CREDENTIALS})
    os.environ["AWS_EC2_METADATA_DISABLED"] = "true"
    return values


def public_subnet(region, requested):
    arguments = ["--subnet-ids", requested] if requested else []
    subnets = ec2.aws(region, "ec2", "describe-subnets", *arguments)["Subnets"]
    for subnet in sorted(subnets, key=lambda item: (not item.get("DefaultForAz", False), item["SubnetId"])):
        if subnet["State"] != "available":
            continue
        tables = ec2.aws(region, "ec2", "describe-route-tables", "--filters",
                         f"Name=vpc-id,Values={subnet['VpcId']}")["RouteTables"]
        explicit = [table for table in tables if any(
            entry.get("SubnetId") == subnet["SubnetId"] for entry in table["Associations"])]
        effective = explicit or [table for table in tables if any(entry.get("Main") for entry in table["Associations"])]
        if any(route.get("DestinationCidrBlock") == "0.0.0.0/0" and route.get("State") == "active"
               and route.get("GatewayId", "").startswith("igw-") for table in effective for route in table["Routes"]):
            return subnet["SubnetId"]
    raise ValueError("No se encontró una subred disponible con ruta pública a Internet en esta región.")


def ssh_cidr(value):
    if not value:
        with urlopen("https://checkip.amazonaws.com", timeout=15) as response:
            value = response.read(128).decode().strip() + "/32"
    network = ipaddress.ip_network(value, strict=True)
    if network.version != 4 or network.prefixlen < 24:
        raise ValueError("Configura SSH_CIDR con tu IPv4 pública seguida de /32.")
    return str(network)


def ensure_key(region, name, path, managed):
    if not managed:
        if not path.is_file():
            raise ValueError("SSH_KEY_PATH debe apuntar a la clave privada del par indicado.")
        ec2.aws(region, "ec2", "describe-key-pairs", "--key-names", name)
        return
    if not path.exists():
        subprocess.run(["ssh-keygen", "-q", "-t", "ed25519", "-N", "", "-f", str(path)], check=True)
        path.chmod(0o600)
    public = path.with_suffix(".pub")
    if not public.is_file():
        raise ValueError("Falta la clave pública local. Conserva juntos los archivos SSH de .state/.")
    existing = ec2.aws(region, "ec2", "describe-key-pairs", "--filters", f"Name=key-name,Values={name}")["KeyPairs"]
    if not existing:
        ec2.aws(region, "ec2", "import-key-pair", "--key-name", name, "--public-key-material", "fileb://" + str(public))


def wait_for_instance(region, instance_id, key, timeout):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        instance = ec2.aws(region, "ec2", "describe-instances", "--instance-ids", instance_id)["Reservations"][0]["Instances"][0]
        status = instance["State"]["Name"]
        if status == "stopped":
            ec2.aws(region, "ec2", "start-instances", "--instance-ids", instance_id)
        elif status in {"terminated", "shutting-down"}:
            raise ValueError("La instancia registrada fue terminada. Usa otro directorio --state-dir para un servidor nuevo.")
        host = instance.get("PublicIpAddress")
        if status == "running" and host:
            probe = subprocess.run([
                "ssh", "-i", str(key), "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=accept-new",
                "-o", "ConnectTimeout=10", "ubuntu@" + host, "true",
            ], capture_output=True, text=True)
            if probe.returncode == 0:
                return host
            if "Permission denied" in probe.stderr or "REMOTE HOST IDENTIFICATION HAS CHANGED" in probe.stderr:
                raise RuntimeError("Revisa la clave SSH o la identidad del host.\n" + probe.stderr)
        print(f"Esperando EC2 y SSH ({status})...", flush=True)
        time.sleep(min(10, max(0, deadline - time.monotonic())))
    raise TimeoutError("EC2 o SSH aún no están listos. Repite el mismo comando para reanudar la espera.")


def provision(values, options):
    for command in ("aws", "git", "ssh", "scp"):
        if not shutil.which(command):
            raise ValueError(f"Instala {command} en esta computadora para continuar.")
    region = values.get("AWS_DEFAULT_REGION") or "us-east-1"
    identity = ec2.check_identity(region)
    print(f"Conexión a AWS validada. Región {region}.", flush=True)
    wizard_path = options.state_dir / "asistente.json"
    if wizard_path.exists():
        wizard = json.loads(wizard_path.read_text())
        if wizard["account"] != identity["Account"] or wizard["region"] != region:
            raise ValueError("El estado pertenece a otra cuenta o región. Usa el .env original u otro --state-dir.")
    else:
        existing_key = values.get("EC2_KEY_PAIR", "")
        existing_path = values.get("SSH_KEY_PATH", "")
        if bool(existing_key) != bool(existing_path):
            raise ValueError("Completa juntos EC2_KEY_PAIR y SSH_KEY_PATH, o deja ambos vacíos para crear un par.")
        key_path = Path(existing_path).expanduser() if existing_path else options.state_dir / "tesis-key"
        if not key_path.is_absolute():
            key_path = (options.env.parent / key_path).resolve()
        wizard = dict(account=identity["Account"], region=region,
                      subnet=public_subnet(region, values.get("EC2_SUBNET_ID")),
                      ssh_cidr=ssh_cidr(values.get("SSH_CIDR")), key_path=str(key_path),
                      key_pair=existing_key or "tesis-r2-" + uuid.uuid4().hex[:12], managed_key=not existing_key,
                      instance_type=values.get("EC2_INSTANCE_TYPE") or "m5.xlarge",
                      disk_gib=int(values.get("EC2_DISK_GIB") or 100),
                      ami=values.get("EC2_AMI") or None, security_group=values.get("EC2_SECURITY_GROUP") or None,
                      profile=values.get("EC2_PROFILE") or None)
    if not 30 <= wizard["disk_gib"] <= 100:
        raise ValueError("EC2_DISK_GIB debe estar entre 30 y 100.")
    print(f"EC2 {wizard['instance_type']} | disco {wizard['disk_gib']} GiB | subred {wizard['subnet']}", flush=True)
    if options.plan:
        print("Plan validado. Ejecuta el mismo comando sin --plan para crear EC2 y preparar Docker.")
        return
    if wizard["managed_key"] and not shutil.which("ssh-keygen"):
        raise ValueError("Instala OpenSSH (ssh-keygen) para generar el par local.")
    ec2.save(wizard_path, wizard)
    key = Path(wizard["key_path"])
    ensure_key(region, wizard["key_pair"], key, wizard["managed_key"])
    instance_path = options.state_dir / "instance.json"
    args = argparse.Namespace(**{name: wizard[name] for name in (
        "region", "subnet", "key_pair", "ssh_cidr", "instance_type", "disk_gib", "ami", "security_group", "profile")},
        state=instance_path, apply=True)
    lock = instance_path.with_suffix(".lock")
    lock.touch(exist_ok=False)
    try:
        print("Creando o recuperando la instancia...", flush=True)
        with redirect_stdout(io.StringIO()):
            ec2.launch(args)
    finally:
        lock.unlink()
    state = json.loads(instance_path.read_text())
    host = wait_for_instance(region, state["instance_id"], key, options.timeout)
    print("Enviando el repositorio y preparando Docker, PostgreSQL, Odoo y R2...", flush=True)
    sync.deploy(host, key)
    print(f"Entorno listo en EC2 {state['instance_id']} ({host}).", flush=True)
    print(f'Abre Odoo con este túnel local: ssh -i "{key}" -L 8069:127.0.0.1:8069 ubuntu@{host}')
    print("Luego visita http://localhost:8069. Resultados remotos en /opt/tesis/repo/aws-lab/results/.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env", type=Path, default=ROOT / ".env")
    parser.add_argument("--state-dir", type=Path, default=ROOT / ".state" / "asistente")
    parser.add_argument("--plan", action="store_true", help="Comprobar acceso y preparar el plan sin crear recursos")
    parser.add_argument("--timeout", type=int, default=900)
    args = parser.parse_args()
    args.env = args.env.resolve()
    args.state_dir = args.state_dir.resolve()
    values = {}
    locked = False
    lock = args.state_dir / "asistente.lock"
    try:
        values = load_environment(args.env)
        args.state_dir.mkdir(parents=True, exist_ok=True)
        lock.touch(exist_ok=False)
        locked = True
        provision(values, args)
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as exc:
        message = str(exc)
        for credential in CREDENTIALS:
            if values.get(credential):
                message = message.replace(values[credential], "[oculto]")
        parser.exit(1, f"{message}\n")
    finally:
        if locked:
            lock.unlink()


if __name__ == "__main__":
    main()
