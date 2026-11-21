"""Provision and inspect one AWS Learner Lab host using AWS CLI v2."""
import argparse
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid

ROOT = Path(__file__).resolve().parent
AUTH_HELP = (
    "Open AWS Details in your Learner Lab and use its current AWS CLI temporary credentials "
    "(access key, secret key AND session token). Run: source aws-lab/use-lab-credentials.sh, "
    "then python3 aws-lab/ec2.py doctor. If the lab identity is still denied, "
    "the course administrator must enable the required EC2 permissions."
)


def aws(region, *arguments):
    result = subprocess.run(
        ["aws", "--region", region, "--no-cli-pager", *arguments, "--output", "json"],
        text=True, capture_output=True, encoding="utf-8",
        env={**os.environ, "AWS_PAGER": ""},
    )
    if result.returncode:
        message = result.stderr.strip()
        if "UnauthorizedOperation" in message or "AccessDenied" in message:
            message += "\n\n" + AUTH_HELP
        raise RuntimeError(message)
    return json.loads(result.stdout or "{}")


def save(path, state):
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def launch(args):
    network = ipaddress.ip_network(args.ssh_cidr, strict=True)
    if network.version != 4 or network.prefixlen < 24:
        raise ValueError("SSH CIDR must be an IPv4 network /24 or narrower, preferably your public IP /32")
    configuration = {key: getattr(args, key) for key in (
        "region", "ami", "subnet", "security_group", "key_pair", "ssh_cidr", "instance_type", "disk_gib", "profile")}
    configuration["bootstrap_sha256"] = hashlib.sha256((ROOT / "user-data.sh").read_bytes()).hexdigest()
    if not args.apply:
        print(json.dumps({"action": "plan", **configuration,
                          "os": "Ubuntu 24.04 amd64", "public_ports": [22],
                          "storage": "encrypted gp3", "apply": "Repeat with --apply"}, indent=2))
        return
    args.state.parent.mkdir(parents=True, exist_ok=True)
    # Keep client token and security group across retries, including interrupted launches.
    state = json.loads(args.state.read_text()) if args.state.exists() else {
        "configuration": configuration, "client_token": str(uuid.uuid4())}
    if state["configuration"] != configuration:
        raise ValueError("State belongs to different parameters. Use a different --state file for a new host")
    if state.get("instance_id"):
        print(json.dumps(state, indent=2))
        return
    check_identity(args.region)
    save(args.state, state)
    subnet = aws(args.region, "ec2", "describe-subnets", "--subnet-ids", args.subnet)["Subnets"][0]
    if not args.ami:
        images = aws(args.region, "ec2", "describe-images", "--owners", "099720109477", "--filters",
                     "Name=name,Values=ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*",
                     "Name=state,Values=available", "Name=architecture,Values=x86_64")["Images"]
        if not images:
            raise ValueError("No Ubuntu 24.04 AMI found in this region")
        state.setdefault("resolved_ami", max(images, key=lambda image: image["CreationDate"])["ImageId"])
    else:
        state["resolved_ami"] = args.ami
    image = aws(args.region, "ec2", "describe-images", "--image-ids", state["resolved_ami"])["Images"][0]
    if image["Architecture"] != "x86_64":
        raise ValueError("This deployment needs an x86_64 Ubuntu 24.04 image")
    if args.security_group:
        state["security_group_id"] = args.security_group
    if not state.get("security_group_id"):
        name = "tesis-r2-" + state["client_token"]
        existing = aws(args.region, "ec2", "describe-security-groups", "--filters",
                       f"Name=vpc-id,Values={subnet['VpcId']}", f"Name=group-name,Values={name}")["SecurityGroups"]
        state["security_group_id"] = existing[0]["GroupId"] if existing else aws(
            args.region, "ec2", "create-security-group", "--group-name", name,
            "--description", "R2 thesis lab SSH access", "--vpc-id", subnet["VpcId"])["GroupId"]
        save(args.state, state)
    if not args.security_group and not state.get("ssh_rule_ready"):
        try:
            aws(args.region, "ec2", "authorize-security-group-ingress", "--group-id", state["security_group_id"],
                "--protocol", "tcp", "--port", "22", "--cidr", args.ssh_cidr)
        except RuntimeError as exc:
            if "InvalidPermission.Duplicate" not in str(exc):
                raise
        state["ssh_rule_ready"] = True
    save(args.state, state)
    request = dict(
        ImageId=state["resolved_ami"], InstanceType=args.instance_type, MinCount=1, MaxCount=1,
        KeyName=args.key_pair, ClientToken=state["client_token"],
        NetworkInterfaces=[dict(DeviceIndex=0, SubnetId=args.subnet, AssociatePublicIpAddress=True,
                                Groups=[state["security_group_id"]])],
        BlockDeviceMappings=[dict(DeviceName=image["RootDeviceName"], Ebs=dict(
            VolumeSize=args.disk_gib, VolumeType="gp3", Encrypted=True, DeleteOnTermination=True))],
        MetadataOptions=dict(HttpTokens="required", HttpEndpoint="enabled"),
        TagSpecifications=[dict(ResourceType="instance", Tags=[dict(Key="Name", Value="tesis-r2-lab")])],
    )
    if args.profile:
        request["IamInstanceProfile"] = {"Name": args.profile}
    request_path = args.state.parent / "launch-request.json"
    save(request_path, request)
    instance = aws(args.region, "ec2", "run-instances", "--cli-input-json", "file://" + str(request_path.resolve()),
                   "--user-data", "file://" + str(ROOT / "user-data.sh"))["Instances"][0]
    state["instance_id"] = instance["InstanceId"]
    save(args.state, state)
    print(json.dumps(state, indent=2))


def check_identity(region):
    identity = aws(region, "sts", "get-caller-identity")
    if ":assumed-role/runserver/" in identity.get("Arn", ""):
        print("The CLI is using the terminal's runserver role. EC2 permissions will be checked.\n" + AUTH_HELP,
              file=sys.stderr)
    return identity


def doctor(region):
    identity = check_identity(region)
    print(json.dumps({"account": identity["Account"], "arn": identity["Arn"]}, indent=2))
    subnets = aws(region, "ec2", "describe-subnets")["Subnets"]
    keys = aws(region, "ec2", "describe-key-pairs")["KeyPairs"]
    print(json.dumps({"subnets": [{key: subnet[key] for key in ("SubnetId", "VpcId", "AvailabilityZone")}
                                  for subnet in subnets], "key_pairs": [key["KeyName"] for key in keys]}, indent=2))
    print("Identity and EC2 discovery passed. Launch permissions are checked when you apply the plan.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("doctor", "launch", "status", "start", "stop"))
    parser.add_argument("--region", default="us-east-1")
    parser.add_argument("--state", type=Path, default=ROOT / ".state" / "instance.json")
    parser.add_argument("--ami", help="Optional Ubuntu 24.04 amd64 AMI override")
    parser.add_argument("--subnet")
    parser.add_argument("--security-group", help="Existing VPC security group with SSH allowed")
    parser.add_argument("--key-pair", help="Existing EC2 key pair, for example the lab key")
    parser.add_argument("--ssh-cidr", help="Your public IPv4 address /32")
    parser.add_argument("--instance-type", default="m5.xlarge")
    parser.add_argument("--disk-gib", type=int, choices=range(30, 101), default=100)
    parser.add_argument("--profile", help="Optional existing instance profile allowed by the lab")
    parser.add_argument("--apply", action="store_true", help="Create the billable EC2 and EBS resources")
    args = parser.parse_args()
    lock = args.state.with_suffix(".lock")
    try:
        if args.action == "doctor":
            doctor(args.region)
        elif args.action == "launch":
            if not all((args.subnet, args.key_pair, args.ssh_cidr)):
                parser.error("launch requires --subnet, --key-pair and --ssh-cidr")
            args.state.parent.mkdir(parents=True, exist_ok=True)
            lock.touch(exist_ok=False)
            try:
                launch(args)
            finally:
                lock.unlink()
        else:
            state = json.loads(args.state.read_text())
            region = state["configuration"]["region"]
            command = "describe-instances" if args.action == "status" else args.action + "-instances"
            print(json.dumps(aws(region, "ec2", command, "--instance-ids", state["instance_id"]), indent=2))
    except (OSError, ValueError, KeyError, RuntimeError) as exc:
        parser.exit(1, f"{exc}\n")


if __name__ == "__main__":
    main()
