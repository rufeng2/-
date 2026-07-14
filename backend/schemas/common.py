"""
通用 Pydantic 模型
"""
from pydantic import BaseModel


class ApiResponse(BaseModel):
    code: int = 200
    msg: str = "成功"
    data: dict | list | None = None


class PaginatedResponse(BaseModel):
    code: int = 200
    msg: str = "成功"
    data: list = []
    total: int = 0
    page: int = 1
    page_size: int = 20
