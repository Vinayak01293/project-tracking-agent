
import logging
import os

from dotenv import load_dotenv
from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI

from agents.orchestration_agent.schemas import RouterIntent

load_dotenv()

logger = logging.getLogger("agent_router")


SYSTEM_PROMPT = """
You are the intent extraction component of a multi-agent
Project Tracking Assistant.

Your responsibility is to understand the user's request and
extract a structured intent.

SUPPORTED PLATFORMS:

1. GitHub
   - list_repositories
   - list_issues
   - list_pull_requests
   - list_starred_repositories

2. Linear
   - list_issues
   - list_projects
   - list_teams

SUPPORTED APPLICATION USERS:
- Jyothir
- Vinayak

RULES:

1. Identify the requested platform.
2. Identify whose external data is being requested.
3. Identify the requested operation.
4. Extract relevant filters.
5. If the user is answering a previous clarification, use the
   previous conversation to complete the original request.
6. Do not treat a clarification reply as a new independent query.
7. If the user identity is not specified, leave target_user_name null.
8. If the platform is not identifiable, leave platform null.
9. If the request is unrelated to GitHub or Linear capabilities,
   set is_supported to false.
10. Do not invent user identities, operations or filters.
11. Do not assume that an Admin's identity is one of the
    external platform users.

IMPORTANT:
A request such as "Show me open pull requests" is supported,
but the target user is missing. Do not classify it as out of scope.
"""


def create_llm():
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("OPENROUTER_MODEL")

    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is missing.")

    if not model:
        raise RuntimeError("OPENROUTER_MODEL is missing.")

    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0,
        max_retries=2,
        timeout=30,
    )


llm = create_llm()

# Function/tool-calling based structured output is useful
# for compatibility with OpenAI-compatible model providers.
intent_llm = llm.with_structured_output(
    RouterIntent,
    method="function_calling",
)


def extract_intent(state: dict) -> dict:
    """
    Extracts user intent using the current conversation context.
    """

    messages = state.get("messages", [])

    # Keep the recent conversation context concise.
    recent_messages = messages[-6:]

    previous_intent = state.get("intent")
    pending = state.get("pending_clarification")

    context_message = f"""
Previous intent:
{previous_intent}

Pending clarification:
{pending}

If a clarification is pending, interpret the latest user message
as a possible answer to that clarification. Preserve all previously
identified intent fields unless the user explicitly changes them.
"""

    try:
        result = intent_llm.invoke(
            [
                SystemMessage(content=SYSTEM_PROMPT),
                SystemMessage(content=context_message),
                *recent_messages,
            ]
        )

        logger.info(
            "INTENT_EXTRACTED",
            extra={
                "platform": result.platform,
                "target_user": result.target_user_name,
                "operation": result.operation,
                "is_supported": result.is_supported,
            },
        )

        # Preserve existing fields when the user is answering
        # a clarification and the LLM returns only the missing value.
        if previous_intent and pending:
            new_intent = result.model_dump()

            for field in ("platform", "operation"):
                if not new_intent.get(field):
                    new_intent[field] = previous_intent.get(field)

            if not new_intent.get("filters"):
                new_intent["filters"] = previous_intent.get(
                    "filters", {}
                )

            return {"intent": new_intent}

        return {"intent": result.model_dump()}

    except Exception:
        logger.exception("INTENT_EXTRACTION_FAILED")
        raise
