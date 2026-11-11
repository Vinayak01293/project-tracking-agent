
import logging

from core.repository.user_repository import UserRepository

logger = logging.getLogger("agent_router")


SUPPORTED_OPERATIONS = {
    "github": {
        "list_repositories",
        "list_issues",
        "list_pull_requests",
        "list_starred_repositories",
    },
    "linear": {
        "list_issues",
        "list_projects",
        "list_teams",
    },
}


class IntentValidator:

    def __init__(self, repository=None):
        self.repository = repository or UserRepository()

    def validate(self, state: dict) -> dict:
        intent = state.get("intent") or {}

        # -------------------------------------------------
        # 1. Out-of-scope validation
        # -------------------------------------------------

        if not intent.get("is_supported", False):
            logger.info("REQUEST_OUT_OF_SCOPE")

            return {
                "status": "out_of_scope",
                "response": "I cannot answer this question",
                "pending_clarification": None,
                "route": None,
            }

        platform = intent.get("platform")
        operation = intent.get("operation")
        target_name = intent.get("target_user_name")

        # -------------------------------------------------
        # 2. Platform validation
        # -------------------------------------------------

        if not platform:
            logger.info("PLATFORM_CLARIFICATION_REQUIRED")

            return {
                "status": "awaiting_clarification",
                "clarification_required": True,
                "pending_clarification": "platform",
                "response": (
                    "Which platform would you like to query: "
                    "GitHub or Linear?"
                ),
                "route": None,
            }

        if platform not in SUPPORTED_OPERATIONS:
            return {
                "status": "out_of_scope",
                "response": "I cannot answer this question",
                "pending_clarification": None,
                "route": None,
            }

        # -------------------------------------------------
        # 3. Operation validation
        # -------------------------------------------------

        if not operation:
            return {
                "status": "awaiting_clarification",
                "clarification_required": True,
                "pending_clarification": "operation",
                "response": (
                    f"What would you like to retrieve from "
                    f"{platform.title()}?"
                ),
                "route": None,
            }

        if operation not in SUPPORTED_OPERATIONS[platform]:
            logger.info(
                "UNSUPPORTED_OPERATION",
                extra={
                    "platform": platform,
                    "operation": operation,
                },
            )

            return {
                "status": "out_of_scope",
                "response": "I cannot answer this question",
                "pending_clarification": None,
                "route": None,
            }

        # -------------------------------------------------
        # 4. Target user resolution
        # -------------------------------------------------

        if not target_name:
            users = self.repository.list_users()

            if not users:
                return {
                    "status": "awaiting_clarification",
                    "clarification_required": True,
                    "pending_clarification": "target_user",
                    "response": (
                        "No users are registered in the User Directory. "
                        "Please create a user before querying platform data."
                    ),
                    "route": None,
                }

            available_users = ", ".join(
                user.name for user in users
            )

            return {
                "status": "awaiting_clarification",
                "clarification_required": True,
                "pending_clarification": "target_user",
                "response": (
                    "Whose data would you like to access? "
                    f"Available users: {available_users}."
                ),
                "route": None,
            }

        users = self.repository.list_users()

        matching_users = [
            user for user in users
            if user.name.strip().casefold() == target_name.strip().casefold()
        ]

        if not matching_users:
            available_users = ", ".join(
                user.name for user in users
            )

            return {
                "status": "awaiting_clarification",
                "clarification_required": True,
                "pending_clarification": "target_user",
                "response": (
                    f"I couldn't find '{target_name}' in the User Directory. "
                    f"Available users: {available_users}."
                ),
                "route": None,
            }

        if len(matching_users) > 1:
            return {
                "status": "awaiting_clarification",
                "clarification_required": True,
                "pending_clarification": "target_user",
                "response": (
                    f"Multiple users match '{target_name}'. "
                    "Please specify the correct user."
                ),
                "route": None,
            }

        target_user = matching_users[0]

        # -------------------------------------------------
        # 5. Validated routing decision
        # -------------------------------------------------

        route = {
            "platform": platform,
            "target_user_id": str(target_user.id),
            "target_user_name": target_user.name,
            "operation": operation,
            "filters": intent.get("filters") or {},
        }

        logger.info(
            "ROUTE_VALIDATED",
            extra={
                "platform": platform,
                "target_user_id": str(target_user.id),
                "operation": operation,
            },
        )

        return {
            "status": "ready",
            "target_user_id": str(target_user.id),
            "pending_clarification": None,
            "route": route,
            "response": (
                f"Request validated. Ready to route to "
                f"the {platform.title()} Agent."
            ),
        }


validator = IntentValidator()
