# backend/app/api/chat.py
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import decrypt_data
from app.api.deps import get_current_user
from app.models.user import User
from app.models.llm_config import LLMConfig
from app.models.neo4j_config import Neo4jConfig
from app.services.qa_agent import QAAgent
import json

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    query: str


@router.post("/stream")
async def chat_stream(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """SSE 流式问答"""

    # 获取用户配置
    llm_result = await db.execute(select(LLMConfig).where(LLMConfig.user_id == current_user.id))
    llm_config = llm_result.scalar_one_or_none()
    if not llm_config:
        raise HTTPException(status_code=400, detail="LLM not configured")

    neo4j_result = await db.execute(select(Neo4jConfig).where(Neo4jConfig.user_id == current_user.id))
    neo4j_config = neo4j_result.scalar_one_or_none()
    if not neo4j_config:
        raise HTTPException(status_code=400, detail="Neo4j not configured")

    llm_dict = {
        "api_key": decrypt_data(llm_config.api_key_encrypted),
        "base_url": llm_config.base_url,
        "model": llm_config.model
    }
    neo4j_dict = {
        "uri": decrypt_data(neo4j_config.uri_encrypted),
        "username": decrypt_data(neo4j_config.username_encrypted),
        "password": decrypt_data(neo4j_config.password_encrypted),
        "database": neo4j_config.database
    }

    agent = QAAgent(current_user.id, db, llm_dict, neo4j_dict)

    async def event_generator():
        async for chunk in agent.astream_chat(req.query):
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.post("/completions")
async def chat_completion(
    req: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """非流式问答（兼容接口）"""
    # 类似实现，收集所有流式结果后一次性返回
    pass
