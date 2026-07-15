"""Shared document parsing, parent-child enrichment and multimodal embedding workflow."""
import base64
import mimetypes
from pathlib import Path
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models import ChunkPermission, Document, DocumentChunk
from backend.services.document_parser import document_parser
from backend.services.document_cleaner import document_cleaner
from backend.services.embedding_service import embedding_service
from backend.services.llm_gateway import llm_gateway
from backend.config import settings
from backend.utils.logger import logger
from backend.services.cache_service import cache_service


def _attach_parent_blocks(chunks: list[dict], max_parent_chars: int = 1800) -> list[dict]:
    """Attach a larger parent block to every small retrieval chunk."""
    groups: list[list[dict]] = []
    current: list[dict] = []
    current_key = None
    current_length = 0
    for item in chunks:
        metadata = item.get("metadata") or {}
        source_key = (metadata.get("page"), metadata.get("sheet"), metadata.get("slide"))
        content_length = len(item.get("content", ""))
        if current and (source_key != current_key or current_length + content_length > max_parent_chars):
            groups.append(current)
            current = []
            current_length = 0
        current_key = source_key
        current.append(item)
        current_length += content_length
    if current:
        groups.append(current)

    enriched = []
    for parent_index, group in enumerate(groups):
        parent_content = "\n".join(item.get("content", "") for item in group).strip()
        parent_id = f"parent-{parent_index}"
        for child_index, item in enumerate(group):
            metadata = dict(item.get("metadata") or {})
            metadata.update({
                "parent_id": parent_id,
                "parent_index": parent_index,
                "child_index": child_index,
                "parent_content": parent_content,
            })
            enriched.append({**item, "metadata": metadata})
    return enriched


async def _enrich_visual_chunks(chunks: list[dict], limit: int = 12) -> tuple[int, int]:
    """Use Qwen-VL for OCR and chart/diagram descriptions before embedding."""
    visual_count = analyzed = 0
    if not settings.DASHSCOPE_API_KEY:
        return sum(bool((item.get("metadata") or {}).get("image_path")) for item in chunks), 0
    for item in chunks:
        metadata = item.get("metadata") or {}
        image_path = metadata.get("image_path", "")
        if not image_path:
            continue
        visual_count += 1
        if analyzed >= limit or not Path(image_path).exists():
            continue
        try:
            mime = mimetypes.guess_type(image_path)[0] or "image/png"
            encoded = base64.b64encode(Path(image_path).read_bytes()).decode("ascii")
            analysis = await llm_gateway.analyze_image(
                f"data:{mime};base64,{encoded}",
                "请完整提取图片中的文字，并描述表格、图表、流程、对象及其位置关系。保持原始数字和单位；只输出可用于企业知识库检索的客观内容。",
            )
            if analysis and not analysis.startswith("[图片分析服务"):
                item["content"] = f"{item.get('content', '')}\n视觉解析:\n{analysis}".strip()
                metadata.update({"vision_analyzed": True, "vision_model": "qwen-vl-plus", "vision_pending": False})
                item["metadata"] = metadata
                analyzed += 1
        except Exception as exc:
            logger.warning("Visual chunk analysis failed: %s", exc)
    return visual_count, analyzed

async def index_document(doc_id: str | UUID, db: AsyncSession) -> int:
    doc_uuid = UUID(str(doc_id))
    doc = (await db.execute(select(Document).where(Document.id == doc_uuid))).scalar_one_or_none()
    if not doc:
        raise ValueError("Document not found")

    doc.status = "parsing"
    doc.error_message = ""
    await db.flush()
    try:
        result = document_parser.parse(doc.storage_path, doc.file_type, doc.chunk_template)
        if not result or not result.chunks:
            raise ValueError("No text could be extracted from the document")
        visual_count, vision_analyzed = await _enrich_visual_chunks(result.chunks)
        cleaned = document_cleaner.clean(result.text, result.chunks)
        cleaned.report.update({"visual_chunks": visual_count, "vision_analyzed": vision_analyzed})
        if not cleaned.chunks:
            raise ValueError("Document cleaning removed all chunks" )
        doc.quality_report = cleaned.report
        chunks = _attach_parent_blocks(cleaned.chunks)
        contents = [item["content"] for item in chunks]
        embeddings = await embedding_service.embed_batch(contents)
        multimodal_inputs = []
        for item in chunks:
            metadata = item.get("metadata") or {}
            multimodal_inputs.append({
                "content": item["content"],
                "image_path": metadata.get("image_path", ""),
            })
        multimodal_embeddings = await embedding_service.embed_multimodal_batch(multimodal_inputs)
        if len(embeddings) != len(contents) or len(multimodal_embeddings) != len(contents):
            raise RuntimeError("Embedding service did not return all vectors")

        old_ids = select(DocumentChunk.id).where(DocumentChunk.document_id == doc.id)
        await db.execute(delete(ChunkPermission).where(ChunkPermission.chunk_id.in_(old_ids)))
        await db.execute(delete(DocumentChunk).where(DocumentChunk.document_id == doc.id))

        for index, (item, embedding, multimodal_embedding) in enumerate(zip(chunks, embeddings, multimodal_embeddings)):
            metadata = item.get("metadata") or {}
            image_path = metadata.get("image_path", "")
            content_type = metadata.get("content_type") or ("image" if image_path else ("table" if metadata.get("sheet") else "text"))
            chunk = DocumentChunk(
                document_id=doc.id,
                chunk_index=index,
                content=item["content"],
                content_type=content_type,
                chunk_meta=metadata,
                embedding=embedding,
                multimodal_embedding=multimodal_embedding,
                image_path=image_path,
                token_count=max(1, len(item["content"]) // 4),
            )
            db.add(chunk)
            await db.flush()
            if doc.department_id:
                db.add(ChunkPermission(chunk_id=chunk.id, department_id=doc.department_id))

        doc.parsed_text = cleaned.text
        doc.page_count = result.page_count
        doc.status = "indexed"
        await db.flush()
        await cache_service.bump_version("index")
        logger.info("Indexed document %s: %s cleaned child chunks, quality=%.2f", doc.id, len(contents), cleaned.report["quality_score"])
        return len(contents)
    except Exception as exc:
        doc.status = "failed"
        doc.error_message = str(exc)[:1000]
        await db.flush()
        logger.error("Index document failed: %s: %s", doc.id, exc, exc_info=True)
        raise
