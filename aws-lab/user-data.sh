#!/usr/bin/env bash
set -euo pipefail
exec > >(tee -a /var/log/tesis-bootstrap.log) 2>&1
export DEBIAN_FRONTEND=noninteractive
source /etc/os-release
if [[ "$ID" != ubuntu ]]; then
  echo 'This bootstrap requires Ubuntu.' >&2
  exit 1
fi
apt-get update
apt-get install -y ca-certificates curl git python3 openssl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $VERSION_CODENAME stable" > /etc/apt/sources.list.d/docker.list
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
usermod -aG docker ubuntu
install -d -o ubuntu -g ubuntu /opt/tesis
touch /opt/tesis/bootstrap-ready
