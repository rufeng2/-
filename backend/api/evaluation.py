"""Enterprise RAG evaluation dataset and automatic evaluation API."""
import json
import re
import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.rag_pipeline import rag_pipeline
from backend.db.models import EvaluationItem, EvaluationRun, User
from backend.db.session import get_db
from backend.schemas.common import ApiResponse
from backend.schemas.evaluation import EvaluationItemCreate, EvaluationItemUpdate, EvaluationRunRequest
from backend.services.llm_gateway import llm_gateway
from backend.utils.auth import require_admin
from backend.tasks.evaluation_task import run_rag_evaluation

router = APIRouter(prefix="/api/evaluation", tags=["RAG评测"])

SEED_ITEMS = [
    ("人事", "员工入职需要提交哪些材料？", ["身份证", "劳动合同", "银行卡"]),
    ("人事", "新员工试用期通常多长？", ["试用期", "转正"]),
    ("人事", "员工如何申请转正？", ["转正", "审批", "考核"]),
    ("人事", "年假天数如何计算？", ["年假", "工龄"]),
    ("人事", "请假需要经过哪些审批？", ["请假", "审批"]),
    ("人事", "员工离职需要办理哪些手续？", ["离职", "交接", "离职证明"]),
    ("财务", "差旅费用如何报销？", ["差旅", "发票", "报销"]),
    ("财务", "报销单提交后多久可以到账？", ["报销", "付款"]),
    ("财务", "哪些费用不能报销？", ["报销", "费用"]),
    ("财务", "借款申请需要什么条件？", ["借款", "审批"]),
    ("采购", "采购申请的完整流程是什么？", ["采购", "询价", "审批"]),
    ("采购", "供应商如何准入？", ["供应商", "资质", "审核"]),
    ("采购", "采购金额达到多少需要招标？", ["招标", "采购金额"]),
    ("合同", "合同签署前需要哪些部门审核？", ["合同", "法务", "审批"]),
    ("合同", "合同用印如何申请？", ["用印", "合同", "审批"]),
    ("合同", "合同到期前如何续签？", ["续签", "到期"]),
    ("IT", "忘记公司邮箱密码怎么办？", ["邮箱", "密码", "重置"]),
    ("IT", "如何申请开通系统权限？", ["权限", "申请", "审批"]),
    ("IT", "办公电脑发生故障如何报修？", ["报修", "IT"]),
    ("IT", "公司数据可以保存到个人网盘吗？", ["网盘", "数据安全"]),
    ("安全", "发现疑似钓鱼邮件应该怎么处理？", ["钓鱼邮件", "安全"]),
    ("安全", "企业敏感数据如何分级？", ["敏感数据", "分级"]),
    ("安全", "账号可以借给同事使用吗？", ["账号", "禁止", "安全"]),
    ("行政", "会议室如何预约？", ["会议室", "预约"]),
    ("行政", "办公用品如何申领？", ["办公用品", "申领"]),
    ("行政", "访客进入办公区需要什么手续？", ["访客", "登记"]),
    ("业务", "客户投诉的处理流程是什么？", ["投诉", "处理", "反馈"]),
    ("业务", "客户信息可以通过私人微信发送吗？", ["客户信息", "合规"]),
    ("合规", "发现利益冲突应该向谁报告？", ["利益冲突", "报告"]),
    ("应急", "发生信息系统故障时如何上报？", ["系统故障", "上报", "应急"]),
]


async def _ensure_seed(db: AsyncSession):
    count = (await db.execute(select(func.count(EvaluationItem.id)))).scalar_one()
    if count:
        return
    for category, question, keywords in SEED_ITEMS:
        db.add(EvaluationItem(question=question, expected_keywords=keywords, category=category))
    await db.flush()


def _serialize(item: EvaluationItem) -> dict:
    return {
        "id": str(item.id), "question": item.question,
        "expected_answer": item.expected_answer,
        "expected_keywords": item.expected_keywords or [],
        "expected_document_titles": item.expected_document_titles or [],
        "expected_chunk_ids": item.expected_chunk_ids or [],
        "expected_pages": item.expected_pages or [], "category": item.category,
        "knowledge_base_id": str(item.knowledge_base_id) if item.knowledge_base_id else "",
        "enabled": item.enabled, "created_at": str(item.created_at),
    }


@router.get("/items", response_model=ApiResponse)
async def list_items(admin: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    await _ensure_seed(db)
    items = (await db.execute(select(EvaluationItem).order_by(EvaluationItem.category, EvaluationItem.created_at))).scalars().all()
    return ApiResponse(data=[_serialize(item) for item in items])


@router.post("/items", response_model=ApiResponse)
async def create_item(request: EvaluationItemCreate, admin: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    kb_id = uuid.UUID(request.knowledge_base_id) if request.knowledge_base_id else None
    item = EvaluationItem(
        question=request.question, expected_answer=request.expected_answer,
        expected_keywords=request.expected_keywords,
        expected_document_titles=request.expected_document_titles,
        expected_chunk_ids=request.expected_chunk_ids, expected_pages=request.expected_pages,
        category=request.category, knowledge_base_id=kb_id,
    )
    db.add(item)
    await db.flush()
    return ApiResponse(msg="评测题已添加", data=_serialize(item))


@router.put("/items/{item_id}", response_model=ApiResponse)
async def update_item(item_id: str, request: EvaluationItemUpdate, admin: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    try:
        item_uuid = uuid.UUID(item_id)
        kb_id = uuid.UUID(request.knowledge_base_id) if request.knowledge_base_id else None
    except ValueError:
        return ApiResponse(code=400, msg="无效的评测题或知识库ID")
    item = (await db.execute(select(EvaluationItem).where(EvaluationItem.id == item_uuid))).scalar_one_or_none()
    if not item:
        return ApiResponse(code=404, msg="评测题不存在")
    item.question = request.question
    item.expected_answer = request.expected_answer
    item.expected_keywords = request.expected_keywords
    item.expected_document_titles = request.expected_document_titles
    item.expected_chunk_ids = request.expected_chunk_ids
    item.expected_pages = request.expected_pages
    item.category = request.category
    item.knowledge_base_id = kb_id
    item.enabled = request.enabled
    await db.flush()
    return ApiResponse(msg="人工标注已保存", data=_serialize(item))

@router.delete("/items/{item_id}", response_model=ApiResponse)
async def delete_item(item_id: str, admin: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    try:
        item_uuid = uuid.UUID(item_id)
    except ValueError:
        return ApiResponse(code=400, msg="无效的评测题ID")
    await db.execute(delete(EvaluationItem).where(EvaluationItem.id == item_uuid))
    return ApiResponse(msg="评测题已删除")


@router.get("/runs", response_model=ApiResponse)
async def list_runs(admin: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    runs = (await db.execute(select(EvaluationRun).order_by(EvaluationRun.created_at.desc()).limit(20))).scalars().all()
    return ApiResponse(data=[{
        "id": str(run.id), "sample_count": run.sample_count, "metrics": run.metrics,
        "details": run.details, "status": run.status, "progress": run.progress,
        "error_message": run.error_message, "options": run.options or {},
        "created_at": str(run.created_at),
    } for run in runs])


@router.post("/run", response_model=ApiResponse)
async def run_evaluation(request: EvaluationRunRequest, admin: dict = Depends(require_admin), db: AsyncSession = Depends(get_db)):
    await _ensure_seed(db)
    db_user = (await db.execute(select(User).where(User.username == admin["username"]))).scalar_one_or_none()
    run = EvaluationRun(
        created_by=db_user.id if db_user else None,
        sample_count=0, metrics={}, details=[], status="pending", progress=0,
        options={"limit": request.limit, "generate_answers": request.generate_answers},
    )
    db.add(run)
    await db.flush()
    await db.commit()
    try:
        task = run_rag_evaluation.delay(str(run.id))
        return ApiResponse(msg="评测任务已提交", data={
            "id": str(run.id), "task_id": task.id, "sample_count": 0,
            "metrics": {}, "details": [], "status": "pending", "progress": 0,
            "options": run.options,
        })
    except Exception as exc:
        run.status = "failed"
        run.error_message = f"评测任务提交失败: {str(exc)[:300]}"
        await db.commit()
        return ApiResponse(code=503, msg=run.error_message)