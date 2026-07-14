"""Back up PostgreSQL, MinIO objects and non-secret configuration."""
import argparse
import hashlib
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import boto3

parser = argparse.ArgumentParser()
parser.add_argument("--output", default="backups")
parser.add_argument("--include-env", action="store_true", help="Include .env; protect the resulting archive")
args = parser.parse_args()
root = Path(__file__).resolve().parents[1]
target = root / args.output / datetime.now().strftime("%Y%m%d-%H%M%S")
target.mkdir(parents=True)
subprocess.run(["docker", "exec", "rag-postgres", "pg_dump", "-U", "ragadmin", "-d", "knowledge_rag", "-Fc", "-f", "/tmp/knowledge_rag.dump"], check=True)
subprocess.run(["docker", "cp", "rag-postgres:/tmp/knowledge_rag.dump", str(target / "postgres.dump")], check=True)
for name in ["docker-compose.yml", "docker-compose.production.yml", ".env.example"]:
    shutil.copy2(root / name, target / name)
if args.include_env and (root / ".env").exists():
    shutil.copy2(root / ".env", target / ".env")
# Copy every MinIO object so database references and binaries stay consistent.
minio_dir = target / "minio"
minio_dir.mkdir()
try:
    import os
    s3 = boto3.client(
        "s3",
        endpoint_url="http://" + os.getenv("MINIO_ENDPOINT", "localhost:9000"),
        aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
    )
    bucket = os.getenv("MINIO_BUCKET", "knowledge-rag")
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket):
        for item in page.get("Contents", []):
            destination = minio_dir / item["Key"]
            destination.parent.mkdir(parents=True, exist_ok=True)
            s3.download_file(bucket, item["Key"], str(destination))
except Exception as exc:
    (target / "minio-warning.txt").write_text(str(exc), encoding="utf-8")
manifest = {"created_at": datetime.now(timezone.utc).isoformat(), "files": {}}
for file in target.iterdir():
    if file.is_file():
        manifest["files"][file.name] = hashlib.sha256(file.read_bytes()).hexdigest()
(target / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
print(target)