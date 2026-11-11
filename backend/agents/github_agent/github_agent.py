
import logging

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage

from agents.github_agent.github_tools import create_github_tools
from core.llm.llm_factory import get_llm
from core.models.users import IntegrationProvider
from core.repository.user_repository import UserRepository
from core.security.encryption import credential_manager

logger = logging.getLogger("github_agent")


GITHUB_SYSTEM_PROMPT = """
You are the GitHub Agent in a multi-agent project tracking system.

Your responsibility is to answer questions about a selected user's
GitHub repositories, issues, pull requests, and starred repositories.

Rules:

1. Use the available GitHub tools to retrieve real data.
2. Never fabricate repositories, issues, pull requests, counts, or dates.
3. Base your response only on the tool results.
4. If the tool returns no records, clearly state that no matching
   records were found.
5. Summarize results clearly and organize multiple records into
   readable lists or tables where appropriate.
6. Include repository names, issue/PR numbers, states, and URLs
   when they are available.
7. Do not claim that an operation was performed if you only retrieved
   information.
8. You are read-only. Never create, update, delete, merge, or modify
   GitHub resources.
9. The selected GitHub account is provided by the application.
   Do not ask the user to choose an account or switch identities.
10. If a request is unrelated to GitHub data, explain that it is
    outside your responsibility.

Keep responses concise but sufficiently informative.
"""


class GitHubAgent:

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
            provider=IntegrationProvider.GITHUB,
        )

        if not integration or not integration.is_active:
            raise ValueError(
                f"{user.name} does not have an active GitHub integration."
            )

        token = credential_manager.decrypt(
            integration.encrypted_secret
        )

        return user, token, integration.external_username

    def _build_agent(self, token: str, username: str):
        tools = create_github_tools(
            token=token,
            username=username,
        )

        return create_agent(
            model=self.llm,
            tools=tools,
            system_prompt=GITHUB_SYSTEM_PROMPT,
        )

    def invoke(
        self,
        user_id: str,
        query: str,
    ) -> dict:
        """
        Execute a GitHub query for the selected directory user.
        """

        try:
            user, token, username = self._get_user_credentials(user_id)

            logger.info(
                "GITHUB_AGENT_STARTED",
                extra={
                    "target_user_id": str(user.id),
                    "target_user": user.name,
                    "platform": "github",
                    "operation": "agent_execution",
                },
            )

            agent = self._build_agent(
                token=token,
                username=username,
            )

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
                "GITHUB_AGENT_COMPLETED",
                extra={
                    "target_user_id": str(user.id),
                    "target_user": user.name,
                    "platform": "github",
                    "status": "success",
                },
            )

            return {
                "success": True,
                "platform": "github",
                "user": user.name,
                "response": answer,
            }

        except Exception:
            logger.exception(
                "GITHUB_AGENT_FAILED",
                extra={
                    "target_user_id": user_id,
                    "platform": "github",
                    "status": "failed",
                },
            )

            return {
                "success": False,
                "platform": "github",
                "response": (
                    "I encountered an error while retrieving "
                    "GitHub information. Please try again."
                ),
            }
