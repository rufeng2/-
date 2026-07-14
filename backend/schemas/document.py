"""
文档相关 Pydantic 模型
"""
from typing import Optional
from pydantic import BaseModel, Field


class DocumentInfo(BaseModel):
    id: str = ""
    title: str = ""
    file_type: str = ""
    file_size: int = 0
    status: str = "pending"
    uploader: str = ""
    department: str = ""
    visibility: str = "internal"
    page_count: int = 0
    knowledge_base_id: str = ""
    knowledge_base_name: str = ""
    chunk_template: str = "general"
    error_message: str = ""
    quality_report: dict = Field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""


class DocumentUpdateRequest(BaseModel):
    title: Optional[str] = None
    visibility: Optional[str] = None
    department_id: Optional[str] = None
