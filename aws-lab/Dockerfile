FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates && rm -rf /var/lib/apt/lists/*
COPY sandbox/r2 /opt/r2
RUN pip install --no-cache-dir /opt/r2
WORKDIR /workspace/repo/sandbox/r2
ENTRYPOINT ["python", "-m", "r2"]
