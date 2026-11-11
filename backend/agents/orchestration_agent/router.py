
import logging

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph

from agents.orchestration_agent.agent_dispatcher import agent_dispatcher
from agents.orchestration_agent.intent_extractor import extract_intent
from agents.orchestration_agent.state import RouterState
from agents.orchestration_agent.validator import validator

logger = logging.getLogger("agent_router")


# ---------------------------------------------------------
# Graph Nodes
# ---------------------------------------------------------

def validate_intent(state: RouterState) -> dict:
    return validator.validate(state)


def ask_clarification(state: RouterState) -> dict:
    response = state["response"]

    logger.info(
        "CLARIFICATION_REQUESTED",
        extra={
            "clarification_type": state.get(
                "pending_clarification"
            )
        },
    )

    return {
        "messages": [AIMessage(content=response)]
    }


def reject_request(state: RouterState) -> dict:
    response = "I cannot answer this question"

    logger.info("REQUEST_REJECTED_OUT_OF_SCOPE")

    return {
        "response": response,
        "messages": [AIMessage(content=response)],
    }

def route_ready(state: RouterState):
    route = state.get("route")

    if not route:
        return {
            "status": "failed",
            "response": "No validated route was found.",
        }

    # Get the latest user message from the conversation.
    latest_user_message = next(
        (
            message
            for message in reversed(state["messages"])
            if isinstance(message, HumanMessage)
        ),
        None,
    )

    if latest_user_message is None:
        return {
            "status": "failed",
            "response": "Unable to retrieve the original user query.",
        }

    query = latest_user_message.content

    if not isinstance(query, str):
        return {
            "status": "failed",
            "response": "The user query must be text.",
        }

    try:
        result = agent_dispatcher.dispatch(
            route=route,
            query=query,
        )

        return {
            "status": "completed" if result.get("success") else "failed",
            "response": result.get(
                "response",
                "The selected agent did not return a response.",
            ),
            "route": route,
        }

    except Exception:
        logger.exception(
            "AGENT_EXECUTION_FAILED",
            extra={
                "platform": route.get("platform"),
                "target_user_id": str(route.get("target_user_id")),
            },
        )

        return {
            "status": "failed",
            "response": (
                "An error occurred while executing the selected agent."
            ),
            "route": route,
        }
# ---------------------------------------------------------
# Conditional Routing
# ---------------------------------------------------------

def determine_next_step(state: RouterState) -> str:

    status = state.get("status")

    if status == "awaiting_clarification":
        return "clarification"

    if status == "out_of_scope":
        return "out_of_scope"

    if status == "ready":
        return "ready"

    raise ValueError(f"Unexpected router status: {status}")


# ---------------------------------------------------------
# Build Router Graph
# ---------------------------------------------------------

def build_router():

    builder = StateGraph(RouterState)

    builder.add_node("extract_intent", extract_intent)
    builder.add_node("validate_intent", validate_intent)

    builder.add_node("ask_clarification", ask_clarification)
    builder.add_node("reject_request", reject_request)
    builder.add_node("route_ready", route_ready)

    builder.add_edge(START, "extract_intent")
    builder.add_edge("extract_intent", "validate_intent")

    builder.add_conditional_edges(
        "validate_intent",
        determine_next_step,
        {
            "clarification": "ask_clarification",
            "out_of_scope": "reject_request",
            "ready": "route_ready",
        },
    )

    builder.add_edge("ask_clarification", END)
    builder.add_edge("reject_request", END)
    builder.add_edge("route_ready", END)

    # In-memory conversation persistence.
    checkpointer = InMemorySaver()

    return builder.compile(checkpointer=checkpointer)


# Shared graph instance for the application.
router_graph = build_router()


# ---------------------------------------------------------
# Public Router Interface
# ---------------------------------------------------------

def process_query(query: str, thread_id: str) -> dict:
    """
    Processes a user query using the Agent Router.

    The same thread_id must be supplied for subsequent
    messages in the same conversation.
    """

    if not query or not query.strip():
        raise ValueError("Query cannot be empty.")

    if not thread_id:
        raise ValueError("thread_id is required.")

    config = {
        "configurable": {
            "thread_id": thread_id,
        },
        "run_name": "Agent Router",
        "tags": [
            "agent-router",
            "intent-extraction",
        ],
        "metadata": {
            "component": "agent_router",
            "thread_id": thread_id,
        },
}

    initial_state = {
        "messages": [
            HumanMessage(content=query.strip())
        ]
    }

    result = router_graph.invoke(
        initial_state,
        config=config,
    )

    return {
        "thread_id": thread_id,
        "status": result["status"],
        "response": result.get("response"),
        "route": result.get("route"),
        "pending_clarification": result.get(
            "pending_clarification"
        ),
    }
