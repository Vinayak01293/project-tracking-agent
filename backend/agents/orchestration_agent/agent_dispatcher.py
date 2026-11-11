
import logging

from agents.github_agent.github_agent import GitHubAgent

logger = logging.getLogger("agent_router")


class AgentDispatcher:

    def __init__(self):
        self.github_agent = GitHubAgent()

        # Add LinearAgent here when its implementation is ready.
        self.linear_agent = None

    def dispatch(self, route: dict, query: str) -> dict:
        platform = route.get("platform")
        user_id = route.get("target_user_id")

        if not platform or not user_id:
            raise ValueError(
                "Validated route is missing platform or target_user_id."
            )

        logger.info(
            "AGENT_DISPATCH_STARTED",
            extra={
                "platform": platform,
                "target_user_id": str(user_id),
                "operation": route.get("operation"),
            },
        )

        if platform == "github":
            result = self.github_agent.invoke(
                user_id=str(user_id),
                query=query,
            )

        elif platform == "linear":
            if self.linear_agent is None:
                return {
                    "success": False,
                    "platform": "linear",
                    "response": "The Linear Agent is not yet available.",
                }

            result = self.linear_agent.invoke(
                user_id=str(user_id),
                query=query,
            )

        else:
            raise ValueError(f"Unsupported platform: {platform}")

        logger.info(
            "AGENT_DISPATCH_COMPLETED",
            extra={
                "platform": platform,
                "target_user_id": str(user_id),
                "status": "success" if result.get("success") else "failed",
            },
        )

        return result


# One dispatcher instance for the application process.
agent_dispatcher = AgentDispatcher()
