"""Restore a pg_dump backup after explicit confirmation."""
import argparse
import json
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("backup")
parser.add_argument("--confirm", required=True)
args = parser.parse_args()
backup = Path(args.backup).resolve()
if args.confirm != "RESTORE":
    raise SystemExit("Pass --confirm RESTORE to perform a destructive restore")
if not (backup / "postgres.dump").exists() or not (backup / "manifest.json").exists():
    raise SystemExit("Invalid backup directory")
subprocess.run(["docker", "cp", str(backup / "postgres.dump"), "rag-postgres:/tmp/knowledge_rag.dump"], check=True)
subprocess.run(["docker", "exec", "rag-postgres", "pg_restore", "-U", "ragadmin", "-d", "knowledge_rag", "--clean", "--if-exists", "/tmp/knowledge_rag.dump"], check=True)
minio_dir = backup / "minio"
if minio_dir.exists():
    import os
    import boto3
    s3 = boto3.client(
        "s3",
        endpoint_url="http://" + os.getenv("MINIO_ENDPOINT", "localhost:9000"),
        aws_access_key_id=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        aws_secret_access_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
    )
    bucket = os.getenv("MINIO_BUCKET", "knowledge-rag")
    for file in minio_dir.rglob("*"):
        if file.is_file():
            s3.upload_file(str(file), bucket, file.relative_to(minio_dir).as_posix())
print(json.dumps({"restored": str(backup)}))