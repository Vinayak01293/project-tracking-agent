
from typing import Any, Literal

from pydantic import BaseModel, Field

Platform = Literal["github", "linear"]


class RouterIntent(BaseModel):
    """
    Structured intent extracted from a user's query.
    """

    is_supported: bool = Field(
        description=(
            "Whether the request falls within the supported "
            "GitHub or Linear capabilities."
        )
    )

    platform: Platform | None = Field(
        default=None,
        description="Target platform: github or linear."
    )

    target_user_name: str | None = Field(
        default=None,
        description=(
            "Name of the user whose external platform data "
            "is requested. Use null if not specified."
        )
    )

    operation: str | None = Field(
        default=None,
        description=(
            "Requested operation, such as list_pull_requests, "
            "list_issues, list_repositories, list_projects, "
            "list_teams or list_starred_repositories."
        )
    )

    filters: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional filters such as state or priority."
    )
