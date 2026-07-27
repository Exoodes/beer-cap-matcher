import os
import shutil
import subprocess
from datetime import datetime
from typing import Any
from urllib.parse import urlparse
from fastapi import APIRouter, Depends, HTTPException
import logging

from src.api.dependencies.auth import verify_admin
from src.api.schemas.common.status_response import StatusResponse
from src.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/backups", tags=["Backups"], dependencies=[Depends(verify_admin)]
)

BACKUP_DIR = "/backups"


@router.post("/", response_model=StatusResponse)
async def create_backup() -> StatusResponse:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    db_file = os.path.join(BACKUP_DIR, f"db_{timestamp}.sql.gz")
    minio_dir = os.path.join(BACKUP_DIR, f"caps_{timestamp}")

    try:
        # 1. Backup Postgres — strip +asyncpg for pg_dump compatibility.
        #    Use Popen to pipe pg_dump | gzip without shell=True (avoids injection).
        pg_url = settings.postgres_database_url.replace("+asyncpg", "")
        with open(db_file, "wb") as f_out:
            pg_dump = subprocess.Popen(
                ["pg_dump", pg_url],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            gzip_proc = subprocess.Popen(
                ["gzip"],
                stdin=pg_dump.stdout,
                stdout=f_out,
                stderr=subprocess.PIPE,
            )
            if pg_dump.stdout:
                pg_dump.stdout.close()  # let pg_dump receive SIGPIPE if gzip exits early
            gzip_proc.communicate()
            pg_dump.wait()

            if pg_dump.returncode != 0:
                raise subprocess.CalledProcessError(pg_dump.returncode, "pg_dump")
            if gzip_proc.returncode != 0:
                raise subprocess.CalledProcessError(gzip_proc.returncode, "gzip")

        # 2. Backup MinIO — pass credentials via MC_HOST_<alias> env var so they
        #    never appear in process arguments (would be visible via `ps aux`).
        raw_ep = settings.minio_endpoint.strip()
        parsed_ep = urlparse(raw_ep if "://" in raw_ep else f"http://{raw_ep}")
        hostport = parsed_ep.netloc or raw_ep.split("/")[0]
        mc_env = {
            **os.environ,
            "MC_HOST_myminio": (
                f"http://{settings.minio_access_key}:{settings.minio_secret_key}@{hostport}"
            ),
        }
        subprocess.run(
            [
                "mc",
                "mirror",
                f"myminio/{settings.minio_original_caps_bucket}",
                minio_dir,
            ],
            check=True,
            env=mc_env,
        )

        return StatusResponse(
            success=True, message=f"Backup {timestamp} created successfully."
        )
    except subprocess.CalledProcessError as e:
        logger.error("Backup failed: %s", e)
        raise HTTPException(
            status_code=500, detail="Backup process failed. Check logs."
        )


@router.get("/")
async def list_backups() -> list[dict[str, Any]]:
    os.makedirs(BACKUP_DIR, exist_ok=True)
    items = []
    for entry in os.listdir(BACKUP_DIR):
        full_path = os.path.join(BACKUP_DIR, entry)
        stat = os.stat(full_path)
        items.append(
            {
                "name": entry,
                "is_dir": os.path.isdir(full_path),
                "size": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            }
        )
    # Sort by newest first
    items.sort(key=lambda x: str(x["created_at"]), reverse=True)
    return items


@router.delete("/{name}", response_model=StatusResponse)
async def delete_backup(name: str) -> StatusResponse:
    # Resolve real paths and confirm the target stays inside BACKUP_DIR.
    # This handles all traversal variants (../../etc, symlinks, etc.)
    backup_root = os.path.realpath(BACKUP_DIR)
    full_path = os.path.realpath(os.path.join(BACKUP_DIR, name))
    if not full_path.startswith(backup_root + os.sep):
        raise HTTPException(status_code=400, detail="Invalid backup name")

    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="Backup not found")

    try:
        if os.path.isdir(full_path):
            shutil.rmtree(full_path)
        else:
            os.remove(full_path)
        return StatusResponse(success=True, message=f"Deleted {name} successfully.")
    except Exception as e:
        logger.error("Failed to delete backup %s: %s", name, e)
        raise HTTPException(status_code=500, detail="Deletion failed")
