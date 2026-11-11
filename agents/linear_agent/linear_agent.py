
import logging

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from agents.linear_agent.linear_tools import create_linear_tools
from core.llm.llm_factory import get_llm
from core.models.users import IntegrationProvider
from core.repository.user_repository import UserRepository
from core.security.encryption import credential_manager

logger = logging.getLogger("linear_agent")


LINEAR_SYSTEM_PROMPT = """
You are the Linear Agent in a multi-agent project tracking system.

Your responsibility is to answer questions about a selected user's
Linear issues, projects, and teams.

Rules:

1. Use the available Linear tools to retrieve real data.
2. Never fabricate issues, projects, teams, counts, or dates.
3. Base your response only on the tool results.
4. If the tool returns no records, clearly state that no matching
   records were found.
5. Summarize results clearly and organize multiple records into
   readable lists or tables where appropriate.
6. Include issue identifiers, titles, states, team names,
   project names, and URLs when available.
7. Do not claim that an operation was performed if you only
   retrieved information.
8. You are read-only. Never create, update, delete, or modify
   Linear resources.
9. The selected Linear account is provided by the application.
   Do not ask the user to choose an account or switch identities.
10. If a request is unrelated to Linear data, explain that it is
    outside your responsibility.

Keep responses concise but sufficiently informative.
"""


class LinearAgent:

    def __init__(
        self,
        user_repository: UserRepository | None = None,
    ):
        self.user_repository = user_repository or UserRepository()

        # Shared model configuration: OpenRouter.
        self.llm = get_llm()

    def _get_user_credentials(self, user_id: str):
        user = self.user_repository.get_user_by_id(user_id)

        if not user:
            raise ValueError("Selected user does not exist.")

        if not user.is_active:
            raise ValueError("Selected user is inactive.")

        integration = self.user_repository.get_integration(
            user_id=user_id,
            provider=IntegrationProvider.LINEAR,
        )

        if not integration or not integration.is_active:
            raise ValueError(
                f"{user.name} does not have an active Linear integration."
            )

        api_key = credential_manager.decrypt(
            integration.encrypted_secret
        )

        return user, api_key

    def _build_agent(self, api_key: str):
        tools = create_linear_tools(api_key=api_key)

        return create_agent(
            model=self.llm,
            tools=tools,
            system_prompt=LINEAR_SYSTEM_PROMPT,
        )

    def invoke(
        self,
        user_id: str,
        query: str,
    ) -> dict:
        """
        Execute a Linear query for the selected directory user.
        """

        try:
            user, api_key = self._get_user_credentials(user_id)

            logger.info(
                "LINEAR_AGENT_STARTED",
                extra={
                    "target_user_id": str(user.id),
                    "target_user": user.name,
                    "platform": "linear",
                    "operation": "agent_execution",
                },
            )

            agent = self._build_agent(api_key=api_key)

            result = agent.invoke(
                {
                    "messages": [
                        HumanMessage(content=query)
                    ]
                }
            )

            final_message = result["messages"][-1]
            answer = final_message.content

            logger.info(
                "LINEAR_AGENT_COMPLETED",
                extra={
                    "target_user_id": str(user.id),
                    "target_user": user.name,
                    "platform": "linear",
                    "status": "success",
                },
            )

            return {
                "success": True,
                "platform": "linear",
                "user": user.name,
                "response": answer,
            }

        except Exception:
            logger.exception(
                "LINEAR_AGENT_FAILED",
                extra={
                    "target_user_id": user_id,
                    "platform": "linear",
                    "status": "failed",
                },
            )

            return {
                "success": False,
                "platform": "linear",
                "response": (
                    "I encountered an error while retrieving "
                    "Linear information. Please try again."
                ),
            }
