"""Conservative document cleaning between parsing and indexing."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass

CLEANER_VERSION = "1.0"
PAGE_NUMBER_RE = re.compile(r"^\s*(?:第\s*)?\d{1,4}\s*(?:页|/\s*\d{1,4})?\s*$", re.I)
END_PUNCTUATION = tuple("。！？!?；;：:")
ZERO_WIDTH = re.compile(r"[\u200b-\u200f\u2060\ufeff]")
CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
MULTI_PUNCT = re.compile(r"([。！？；!?;])\1+")


@dataclass
class CleanResult:
    text: str
    chunks: list[dict]
    report: dict


class DocumentCleaner:
    """Remove retrieval noise while retaining structure and evidence metadata."""

    @staticmethod
    def normalize_text(text: str) -> str:
        if not text:
            return ""
        text = unicodedata.normalize("NFKC", str(text))
        text = ZERO_WIDTH.sub("", text)
        text = CONTROL.sub("", text)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("\u00a0", " ")
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r" *\n *", "\n", text)
        text = MULTI_PUNCT.sub(r"\1", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _is_heading(line: str) -> bool:
        value = line.strip()
        if not value or len(value) > 32:
            return False
        if value.startswith(("#", "【", "[")):
            return True
        if re.match(r"^(?:第[一二三四五六七八九十百\d]+[章节部分]|\d+(?:\.\d+)*[、.])", value):
            return True
        return len(value) <= 16 and not value.endswith(END_PUNCTUATION) and "|" not in value

    def repair_line_breaks(self, text: str) -> str:
        lines = self.normalize_text(text).splitlines()
        output: list[str] = []
        for raw in lines:
            line = raw.strip()
            if not line:
                if output and output[-1] != "":
                    output.append("")
                continue
            if PAGE_NUMBER_RE.fullmatch(line):
                continue
            if not output or output[-1] == "":
                output.append(line)
                continue
            previous = output[-1]
            join_line = (
                not previous.endswith(END_PUNCTUATION)
                and not self._is_heading(previous)
                and not self._is_heading(line)
                and "|" not in previous
                and "|" not in line
                and not re.match(r"^[\-•●▪◦]\s*", line)
            )
            if join_line:
                separator = " " if previous[-1:].isascii() and line[:1].isascii() else ""
                output[-1] = previous + separator + line
            else:
                output.append(line)
        return re.sub(r"\n{3,}", "\n\n", "\n".join(output)).strip()

    @staticmethod
    def _line_quality(line: str) -> float:
        if not line:
            return 1.0
        valid = sum(
            char.isalnum() or "\u4e00" <= char <= "\u9fff" or char.isspace()
            or char in "，。！？；：、,.!?;:()（）[]【】/|+-_%￥¥@"
            for char in line
        )
        return valid / len(line)

    def clean_ocr_text(self, text: str) -> tuple[str, int]:
        kept, removed = [], 0
        for line in self.normalize_text(text).splitlines():
            if len(line.strip()) >= 5 and self._line_quality(line) < 0.65:
                removed += 1
                continue
            kept.append(line)
        return "\n".join(kept).strip(), removed

    def _repeated_noise_lines(self, chunks: list[dict]) -> set[str]:
        page_lines: dict[str, set[str]] = defaultdict(set)
        pages = set()
        for item in chunks:
            metadata = item.get("metadata") or {}
            page = metadata.get("page") or metadata.get("slide")
            if page is None:
                continue
            pages.add(str(page))
            for line in self.normalize_text(item.get("content", "")).splitlines():
                line = line.strip()
                if 2 <= len(line) <= 60:
                    page_lines[line].add(str(page))
        minimum = max(3, int(len(pages) * 0.6 + 0.5))
        return {line for line, found_pages in page_lines.items() if len(found_pages) >= minimum}

    @staticmethod
    def _fingerprint(text: str) -> str:
        normalized = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "", text).lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest() if normalized else ""

    def _enhance_table(self, content: str, metadata: dict) -> tuple[str, int]:
        if not metadata.get("sheet"):
            return content, 0
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        normalized = []
        rows = 0
        for line in lines:
            if "|" in line:
                cells = [re.sub(r"\s+", " ", cell.strip()) for cell in line.split("|")]
                normalized.append(" | ".join(cell for cell in cells if cell))
                rows += 1
            else:
                normalized.append(line)
        sheet_label = f"【工作表: {metadata['sheet']}】"
        if not normalized or not normalized[0].startswith("【工作表:"):
            normalized.insert(0, sheet_label)
        return "\n".join(normalized), rows

    def clean(self, text: str, chunks: list[dict]) -> CleanResult:
        original_chars = sum(len(item.get("content", "")) for item in chunks)
        repeated_noise = self._repeated_noise_lines(chunks)
        seen: set[str] = set()
        cleaned_chunks: list[dict] = []
        removed_noise_lines = removed_ocr_lines = duplicate_chunks = empty_chunks = table_rows = 0

        for item in chunks:
            metadata = dict(item.get("metadata") or {})
            content = self.normalize_text(item.get("content", ""))
            before_lines = content.splitlines()
            filtered_lines = []
            for line in before_lines:
                stripped = line.strip()
                if PAGE_NUMBER_RE.fullmatch(stripped) or stripped in repeated_noise:
                    removed_noise_lines += 1
                    continue
                filtered_lines.append(line)
            content, removed = self.clean_ocr_text("\n".join(filtered_lines))
            removed_ocr_lines += removed
            content = self.repair_line_breaks(content)
            content, row_count = self._enhance_table(content, metadata)
            table_rows += row_count
            if not content:
                empty_chunks += 1
                continue
            fingerprint = self._fingerprint(content)
            if fingerprint and fingerprint in seen:
                duplicate_chunks += 1
                continue
            seen.add(fingerprint)
            metadata.update({
                "cleaner_version": CLEANER_VERSION,
                "cleaned": True,
                "original_chars": len(item.get("content", "")),
                "cleaned_chars": len(content),
            })
            if row_count:
                metadata["table_row_count"] = row_count
            cleaned_chunks.append({**item, "content": content, "metadata": metadata})

        cleaned_chars = sum(len(item["content"]) for item in cleaned_chunks)
        replacement_chars = sum(item["content"].count("�") for item in cleaned_chunks)
        replacement_ratio = replacement_chars / max(1, cleaned_chars)
        duplicate_ratio = duplicate_chunks / max(1, len(chunks))
        retained_ratio = cleaned_chars / max(1, original_chars)
        score = 1.0
        warnings = []
        if cleaned_chars < 50:
            score -= 0.45; warnings.append("清洗后有效文本少于50字符")
        if replacement_ratio > 0.01:
            score -= min(0.25, replacement_ratio * 2); warnings.append("文本中存在较多乱码替换符")
        if duplicate_ratio > 0.3:
            score -= 0.15; warnings.append("重复分块比例较高")
        if retained_ratio < 0.45:
            score -= 0.15; warnings.append("清洗移除内容超过55%，请检查是否过度清洗")
        if not cleaned_chunks:
            score = 0.0; warnings.append("没有可索引的有效分块")
        score = round(max(0.0, min(1.0, score)), 4)
        report = {
            "cleaner_version": CLEANER_VERSION,
            "original_chars": original_chars,
            "cleaned_chars": cleaned_chars,
            "original_chunks": len(chunks),
            "cleaned_chunks": len(cleaned_chunks),
            "removed_noise_lines": removed_noise_lines,
            "removed_ocr_lines": removed_ocr_lines,
            "duplicate_chunks": duplicate_chunks,
            "empty_chunks": empty_chunks,
            "table_rows": table_rows,
            "replacement_ratio": round(replacement_ratio, 6),
            "retained_ratio": round(retained_ratio, 4),
            "quality_score": score,
            "warnings": warnings,
        }
        cleaned_text = self.repair_line_breaks(self.normalize_text(text))
        return CleanResult(text=cleaned_text, chunks=cleaned_chunks, report=report)


document_cleaner = DocumentCleaner()