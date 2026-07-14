"""Prompt definitions for the enterprise RAG chain."""
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from backend.core.system_prompt import SYSTEM_PROMPT


RAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="history", optional=True),
    (
        "human",
        """## 检索到的知识库内容
{context}

## 用户问题
{question}

请严格基于知识库内容回答，并在相关结论后标注引用编号。""",
    ),
])

