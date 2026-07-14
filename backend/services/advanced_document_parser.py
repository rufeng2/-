"""Layout-aware PDF and DOCX extraction with image-position metadata."""
from __future__ import annotations

from pathlib import Path
import shutil
from typing import Callable

from backend.utils.logger import logger

try:
    import fitz
    HAS_FITZ = True
except ImportError:
    fitz = None
    HAS_FITZ = False

try:
    import docx
    from docx.oxml.ns import qn
    from docx.oxml.text.paragraph import CT_P
    from docx.oxml.table import CT_Tbl
    from docx.text.paragraph import Paragraph
    from docx.table import Table
    HAS_DOCX = True
except ImportError:
    docx = None
    qn = None
    HAS_DOCX = False


class AdvancedDocumentParser:
    def __init__(self, chunker: Callable):
        self.chunker = chunker

    @staticmethod
    def _clear_asset_dir(path: Path) -> None:
        target = path.parent / f"{path.stem}_assets"
        if target.exists():
            shutil.rmtree(target)
    @staticmethod
    def _asset_dir(path: Path) -> Path:
        target = path.parent / f"{path.stem}_assets"
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)
        return target

    @staticmethod
    def _ordered_blocks(page) -> list[tuple]:
        blocks = [block for block in page.get_text("blocks") if len(block) >= 5 and str(block[4]).strip()]
        width = float(page.rect.width)
        left = [b for b in blocks if b[2] <= width * 0.58]
        right = [b for b in blocks if b[0] >= width * 0.42]
        spanning = [b for b in blocks if b not in left and b not in right]
        if len(left) >= 2 and len(right) >= 2:
            return sorted(spanning, key=lambda b: (b[1], b[0])) + sorted(left, key=lambda b: (b[1], b[0])) + sorted(right, key=lambda b: (b[1], b[0]))
        return sorted(blocks, key=lambda b: (round(b[1] / 8), b[0]))

    def parse_pdf(self, path: Path, template: str, result_factory):
        if not HAS_FITZ:
            return None
        document = fitz.open(path)
        assets = self._asset_dir(path)
        chunks, pages_text = [], []
        extracted_images = 0
        for page_index, page in enumerate(document):
            page_number = page_index + 1
            blocks = self._ordered_blocks(page)
            block_texts = []
            for block_index, block in enumerate(blocks):
                value = str(block[4]).strip()
                if not value:
                    continue
                block_texts.append(value)
                metadata = {
                    "page": page_number,
                    "block": block_index + 1,
                    "bbox": [round(float(v), 2) for v in block[:4]],
                    "parser": "pymupdf-layout",
                }
                chunks.extend(self.chunker(value, metadata, template))
            page_text = "\n\n".join(block_texts)
            pages_text.append(page_text)

            image_entries = page.get_images(full=True)
            for image_index, image in enumerate(image_entries, 1):
                try:
                    xref = image[0]
                    payload = document.extract_image(xref)
                    ext = payload.get("ext", "png")
                    image_path = assets / f"page-{page_number}-image-{image_index}.{ext}"
                    image_path.write_bytes(payload["image"])
                    rects = page.get_image_rects(xref)
                    bbox = [round(float(v), 2) for v in rects[0]] if rects else []
                    caption = f"PDF 第{page_number}页内嵌图片 {image_index}"
                    chunks.append({"content": caption, "metadata": {
                        "page": page_number, "image_index": image_index,
                        "bbox": bbox, "image_path": str(image_path),
                        "parser": "pymupdf-image", "content_type": "image",
                    }})
                    extracted_images += 1
                except Exception as exc:
                    logger.warning("PDF image extraction failed on page %s: %s", page_number, exc)

            # A text-poor page is indexed as a rendered image so scanned PDFs remain searchable multimodally.
            if len(page_text.strip()) < 20:
                scan_path = assets / f"page-{page_number}-scan.png"
                page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False).save(scan_path)
                chunks.append({"content": f"扫描 PDF 第{page_number}页", "metadata": {
                    "page": page_number, "image_path": str(scan_path),
                    "parser": "pymupdf-scan", "content_type": "image", "scanned_page": True,
                }})
        document.close()
        logger.info("PyMuPDF parsed %s pages and %s embedded images", len(pages_text), extracted_images)
        return result_factory("\n\n".join(pages_text), chunks, len(pages_text))

    def parse_docx(self, path: Path, template: str, result_factory):
        if not HAS_DOCX:
            return None
        document = docx.Document(str(path))
        self._clear_asset_dir(path)
        chunks, full_parts = [], []
        assets = None
        paragraph_index = table_index = 0

        for child in document.element.body.iterchildren():
            if isinstance(child, CT_P):
                paragraph_index += 1
                paragraph = Paragraph(child, document)
                value = paragraph.text.strip()
                if value:
                    full_parts.append(value)
                    chunks.extend(self.chunker(value, {
                        "paragraph": paragraph_index, "block_order": len(full_parts), "parser": "python-docx"
                    }, template))
                for blip in paragraph._p.xpath('.//a:blip'):
                    rel_id = blip.get(qn('r:embed'))
                    if not rel_id or rel_id not in document.part.related_parts:
                        continue
                    if assets is None:
                        assets = self._asset_dir(path)
                    part = document.part.related_parts[rel_id]
                    suffix = Path(str(part.partname)).suffix or ".png"
                    image_path = assets / f"paragraph-{paragraph_index}-{rel_id}{suffix}"
                    image_path.write_bytes(part.blob)
                    caption = f"Word 第{paragraph_index}段附近的内嵌图片"
                    full_parts.append(caption)
                    chunks.append({"content": caption, "metadata": {
                        "paragraph": paragraph_index, "block_order": len(full_parts), "image_path": str(image_path),
                        "parser": "python-docx-image", "content_type": "image",
                    }})
            elif isinstance(child, CT_Tbl):
                table_index += 1
                table = Table(child, document)
                rows = []
                for row in table.rows:
                    values = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                    if any(values):
                        rows.append(" | ".join(values))
                if rows:
                    table_text = f"【Word表格 {table_index}】\n" + "\n".join(rows)
                    full_parts.append(table_text)
                    chunks.extend(self.chunker(table_text, {
                        "table": table_index, "block_order": len(full_parts),
                        "parser": "python-docx-table", "content_type": "table"
                    }, "table"))
        return result_factory("\n\n".join(full_parts), chunks, max(1, paragraph_index // 20 + 1))
