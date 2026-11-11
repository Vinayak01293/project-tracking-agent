
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from agents.orchestration_agent.router import process_query

logger = logging.getLogger("agent_router")

router = APIRouter(
    prefix="/api/chat",
    tags=["Agent Router"],
)


class ChatRequest(BaseModel):
    query: str = Field(min_length=1)
    thread_id: str = Field(min_length=1)


class ChatResponse(BaseModel):
    thread_id: str
    status: str
    response: str | None
    route: dict | None
    pending_clarification: str | None


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest):

    try:
        result = process_query(
            query=request.query,
            thread_id=request.thread_id,
        )

        return result

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except Exception:
        logger.exception("CHAT_REQUEST_FAILED")

        raise HTTPException(
            status_code=500,
            detail="Unable to process the request.",
        )
