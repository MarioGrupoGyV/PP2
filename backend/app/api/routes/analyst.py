from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.agents.analyst_agent import ProcessAnalystAgent
from app.core.database import get_db
from app.schemas.analyst import (
    AnalystChatRequest,
    AnalystChatResponse,
    AnalystStatusResponse,
)
from app.services.analyst_service import get_process_analyst_agent

router = APIRouter()
DbSession = Annotated[Session, Depends(get_db)]
Agent = Annotated[ProcessAnalystAgent, Depends(get_process_analyst_agent)]


@router.get("/status", response_model=AnalystStatusResponse)
def get_analyst_status(agent: Agent) -> AnalystStatusResponse:
    return agent.status()


@router.post("/chat", response_model=AnalystChatResponse)
def chat_with_analyst(
    data: AnalystChatRequest,
    db: DbSession,
    agent: Agent,
) -> AnalystChatResponse:
    return agent.chat(db, data)
