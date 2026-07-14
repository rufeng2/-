"""
对话相关 Pydantic 模型
"""
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=4000)
    conversation_id: str = ""
    category: str = ""
    knowledge_base_ids: list[str] = Field(default_factory=list)
    image_ids: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str = ""
    conversation_id: str = ""
    references: list[dict] = []


class ConversationInfo(BaseModel):
    id: str = ""
    title: str = ""
    created_at: str = ""
    updated_at: str = ""


class MessageInfo(BaseModel):
    id: str = ""
    role: str = ""
    content: str = ""
    references: list[dict] = []
    feedback: int = 0
    created_at: str = ""


class FeedbackRequest(BaseModel):
    message_id: str = ""
    rating: int = Field(..., ge=-1, le=1)
    comment: str = ""
