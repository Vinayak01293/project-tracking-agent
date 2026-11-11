
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class RouterState(TypedDict):
    # Conversation history
    messages: Annotated[list[BaseMessage], add_messages]

    # Extracted intent
    intent: dict[str, Any] | None

    # Resolved application user
    target_user_id: str | None

    # Clarification state
    pending_clarification: str | None

    # Router execution status
    status: str

    # Response returned to the caller
    response: str | None

    # Validated routing decision
    route: dict[str, Any] | None

    # Whether this request required clarification
    clarification_required: bool

    # Query to be sent to the specialist agent
    agent_query: str | None
