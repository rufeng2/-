from pydantic import BaseModel, Field


class EvaluationItemCreate(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)
    expected_answer: str = ""
    expected_keywords: list[str] = Field(default_factory=list)
    expected_document_titles: list[str] = Field(default_factory=list)
    expected_chunk_ids: list[str] = Field(default_factory=list)
    expected_pages: list[int] = Field(default_factory=list)
    category: str = "通用"
    knowledge_base_id: str = ""


class EvaluationItemUpdate(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)
    expected_answer: str = ""
    expected_keywords: list[str] = Field(default_factory=list)
    expected_document_titles: list[str] = Field(default_factory=list)
    expected_chunk_ids: list[str] = Field(default_factory=list)
    expected_pages: list[int] = Field(default_factory=list)
    category: str = "通用"
    knowledge_base_id: str = ""
    enabled: bool = True

class EvaluationRunRequest(BaseModel):
    limit: int = Field(10, ge=1, le=100)
    generate_answers: bool = False