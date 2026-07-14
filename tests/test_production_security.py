from pathlib import Path
from tempfile import NamedTemporaryFile
from zipfile import ZipFile

import pytest

from backend.security.file_security import validate_file
from backend.security.rbac import has_permission


def test_rbac_matrix():
    assert has_permission("admin", "system.manage")
    assert has_permission("viewer", "documents.read")
    assert not has_permission("viewer", "documents.write")
    assert has_permission("editor", "evaluation.run")


def test_pdf_signature_validation(tmp_path: Path):
    valid = tmp_path / "ok.pdf"
    valid.write_bytes(b"%PDF-1.7\n")
    validate_file(str(valid), ".pdf")
    invalid = tmp_path / "bad.pdf"
    invalid.write_bytes(b"not a pdf")
    with pytest.raises(ValueError, match="file_signature_mismatch"):
        validate_file(str(invalid), ".pdf")


def test_office_zip_validation(tmp_path: Path):
    file = tmp_path / "sample.docx"
    with ZipFile(file, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
    validate_file(str(file), ".docx")