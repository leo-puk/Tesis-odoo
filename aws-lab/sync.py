"""Upload tracked working-tree sources and AWS helpers to the lab host over SSH."""
import argparse
import io
import json
from pathlib import Path
import subprocess
import tarfile
import tempfile
import uuid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, help="EC2 public DNS or IPv4")
    parser.add_argument("--key", required=True, type=Path, help="Existing SSH private key")
    args = parser.parse_args()
    deploy(args.host, args.key)


def deploy(host, key):
    repo = Path(__file__).resolve().parent.parent
    tracked = subprocess.check_output(["git", "-C", str(repo), "ls-files", "-z"]).decode().split("\0")
    additions = subprocess.check_output([
        "git", "-C", str(repo), "ls-files", "--others", "--exclude-standard", "-z", "--", "sandbox/r2"
    ]).decode().split("\0")
    helpers = [str(p.relative_to(repo)).replace("\\", "/") for p in (repo / "aws-lab").iterdir()
               if p.is_file() and p.suffix in {".py", ".sh", ".md", ".yml"}]
    helpers += ["aws-lab/Dockerfile", "aws-lab/Dockerfile.dockerignore"]
    remote = "ubuntu@" + host
    destination = "/tmp/tesis-" + uuid.uuid4().hex + ".tar.gz"
    with tempfile.TemporaryDirectory() as temporary:
        archive = Path(temporary) / "source.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            for name in sorted(set(tracked + additions + helpers) - {""}):
                source = repo / name
                if source.is_file():
                    tar.add(source, arcname=name, recursive=False)
            revision = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
            changes = subprocess.check_output(["git", "-C", str(repo), "status", "--porcelain"], text=True)
            payload = json.dumps(dict(git_sha=revision, working_tree=changes), indent=2).encode("utf-8")
            metadata = tarfile.TarInfo("aws-lab/source-revision.json")
            metadata.size = len(payload)
            tar.addfile(metadata, io.BytesIO(payload))
        options = ["-i", str(key), "-o", "StrictHostKeyChecking=accept-new", "-o", "BatchMode=yes",
                   "-o", "ConnectTimeout=15"]
        subprocess.run(["scp", *options, str(archive), remote + ":" + destination], check=True)
        command = (
            "sudo cloud-init status --wait && test -f /opt/tesis/bootstrap-ready && "
            "mkdir -p /opt/tesis/repo && tar --no-same-owner -xzf " + destination +
            " -C /opt/tesis/repo && rm " + destination +
            " && bash /opt/tesis/repo/aws-lab/setup.sh"
        )
        subprocess.run(["ssh", *options, remote, command], check=True)


if __name__ == "__main__":
    main()
