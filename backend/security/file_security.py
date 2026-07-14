"""File signature validation and optional ClamAV INSTREAM scanning."""
import socket
import struct
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from backend.config import settings

SIGNATURES = {
    ".pdf": (b"%PDF-",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
    ".bmp": (b"BM",),
    ".tiff": (b"II*\x00", b"MM\x00*"),
}
OOXML = {".docx", ".xlsx", ".pptx"}
TEXT = {".txt", ".md", ".csv"}


def validate_file(path: str, extension: str) -> None:
    ext = extension.lower()
    data = Path(path).read_bytes()[:16]
    if ext in SIGNATURES and not any(data.startswith(sig) for sig in SIGNATURES[ext]):
        raise ValueError("file_signature_mismatch")
    if ext in OOXML:
        try:
            with ZipFile(path) as archive:
                if "[Content_Types].xml" not in archive.namelist():
                    raise ValueError("invalid_office_file")
        except BadZipFile as exc:
            raise ValueError("invalid_office_file") from exc
    if ext not in SIGNATURES and ext not in OOXML and ext not in TEXT:
        raise ValueError("unsupported_file_type")


def scan_with_clamav(path: str) -> None:
    if not settings.CLAMAV_ENABLED:
        return
    try:
        with socket.create_connection((settings.CLAMAV_HOST, settings.CLAMAV_PORT), timeout=10) as sock:
            sock.sendall(b"zINSTREAM\x00")
            with open(path, "rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    sock.sendall(struct.pack(">I", len(chunk)) + chunk)
            sock.sendall(struct.pack(">I", 0))
            result = sock.recv(4096).decode("utf-8", "replace")
        if "FOUND" in result:
            raise ValueError("malware_detected")
        if "OK" not in result:
            raise RuntimeError(f"unexpected_clamav_response:{result[:100]}")
    except ValueError:
        raise
    except Exception:
        if settings.FILE_SCAN_FAIL_CLOSED:
            raise ValueError("virus_scanner_unavailable")