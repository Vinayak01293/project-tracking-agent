
import logging

import httpx
from langchain_core.tools import tool

logger = logging.getLogger("linear_agent")

LINEAR_API_URL = "https://api.linear.app/graphql"


class LinearAPIError(Exception):
    """Raised when a Linear API request fails."""


def create_linear_tools(api_key: str):
    """
    Creates Linear tools scoped to one registered user's API key.

    The API key is captured in the tool closures.
    The LLM cannot choose or override the authenticated identity.
    """

    headers = {
        "Authorization": api_key,
        "Content-Type": "application/json",
    }

    def make_request(query: str, variables: dict | None = None) -> dict:
        try:
            response = httpx.post(
                LINEAR_API_URL,
                headers=headers,
                json={
                    "query": query,
                    "variables": variables or {},
                },
                timeout=20.0,
            )

            if response.status_code in (401, 403):
                raise LinearAPIError(
                    "Linear authentication failed or API access was denied. "
                    "Check the stored API key and its permissions."
                )

            response.raise_for_status()
            result = response.json()

            if result.get("errors"):
                logger.error(
                    "LINEAR_GRAPHQL_ERROR",
                    extra={
                        "errors": result["errors"],
                    },
                )
                raise LinearAPIError(
                    "Linear returned a GraphQL error. "
                    "Check the requested resource and API permissions."
                )

            return result.get("data") or {}

        except LinearAPIError:
            raise

        except httpx.TimeoutException as exc:
            raise LinearAPIError(
                "Linear API request timed out."
            ) from exc

        except httpx.HTTPStatusError as exc:
            logger.exception(
                "LINEAR_API_HTTP_ERROR",
                extra={
                    "status": exc.response.status_code,
                },
            )
            raise LinearAPIError(
                f"Linear API returned HTTP {exc.response.status_code}."
            ) from exc

        except httpx.RequestError as exc:
            logger.exception("LINEAR_API_CONNECTION_ERROR")
            raise LinearAPIError(
                "Unable to connect to the Linear API."
            ) from exc

        except ValueError as exc:
            logger.exception("LINEAR_API_INVALID_RESPONSE")
            raise LinearAPIError(
                "Linear returned an invalid response."
            ) from exc

    def get_viewer() -> dict:
        """Resolve the identity associated with the API key."""

        data = make_request(
            """
            query {
                viewer {
                    id
                    name
                    displayName
                    email
                }
            }
            """
        )

        viewer = data.get("viewer")

        if not viewer:
            raise LinearAPIError(
                "Unable to identify the authenticated Linear user."
            )

        return viewer

    @tool
    def list_issues(
        state: str = "open",
        limit: int = 30,
    ) -> dict:
        """
        List issues assigned to the authenticated Linear user.

        Use this when the user asks to show or list their Linear issues.

        Args:
            state: Issue state filter: open, completed, or all.
            limit: Maximum number of issues to return (1-100).
        """

        if state not in {"open", "completed", "all"}:
            state = "open"

        limit = max(1, min(limit, 100))

        viewer = get_viewer()

        data = make_request(
            """
            query AssignedIssues($userId: ID!, $limit: Int!) {
                issues(
                    filter: {
                        assignee: {
                            id: {
                                eq: $userId
                            }
                        }
                    }
                    first: $limit
                ) {
                    nodes {
                        id
                        identifier
                        title
                        description
                        priority
                        url
                        createdAt
                        updatedAt
                        dueDate
                        state {
                            name
                            type
                        }
                        team {
                            name
                            key
                        }
                        project {
                            name
                        }
                        assignee {
                            name
                        }
                    }
                }
            }
            """,
            variables={
                "userId": viewer["id"],
                "limit": limit,
            },
        )

        raw_issues = (
            data.get("issues", {}).get("nodes", [])
        )

        issues = []

        for issue in raw_issues:
            issue_state = (
                issue.get("state") or {}
            )

            state_type = issue_state.get("type")

            # Linear workflow types:
            # backlog, unstarted, started, completed, canceled.
            if state == "open" and state_type in {
                "completed",
                "canceled",
            }:
                continue

            if state == "completed" and state_type != "completed":
                continue

            issues.append(
                {
                    "identifier": issue.get("identifier"),
                    "title": issue.get("title"),
                    "description": issue.get("description"),
                    "priority": issue.get("priority"),
                    "state": issue_state.get("name"),
                    "state_type": state_type,
                    "team": (
                        issue.get("team") or {}
                    ).get("name"),
                    "team_key": (
                        issue.get("team") or {}
                    ).get("key"),
                    "project": (
                        issue.get("project") or {}
                    ).get("name"),
                    "assignee": (
                        issue.get("assignee") or {}
                    ).get("name"),
                    "url": issue.get("url"),
                    "created_at": issue.get("createdAt"),
                    "updated_at": issue.get("updatedAt"),
                    "due_date": issue.get("dueDate"),
                }
            )

        return {
            "user": viewer.get("name"),
            "count": len(issues),
            "filter": state,
            "issues": issues,
        }

    @tool
    def list_projects(limit: int = 30) -> dict:
        """
        List projects accessible to the authenticated Linear account.

        Use this when the user asks to show or list Linear projects.

        Args:
            limit: Maximum number of projects to return (1-100).
        """

        limit = max(1, min(limit, 100))

        viewer = get_viewer()

        data = make_request(
            """
            query Projects($limit: Int!) {
                projects(first: $limit) {
                    nodes {
                        id
                        name
                        description
                        state
                        progress
                        url
                        startDate
                        targetDate
                        teams {
                            nodes {
                                name
                                key
                            }
                        }
                    }
                }
            }
            """,
            variables={
                "limit": limit,
            },
        )

        raw_projects = (
            data.get("projects", {}).get("nodes", [])
        )

        projects = [
            {
                "name": project.get("name"),
                "description": project.get("description"),
                "state": project.get("state"),
                "progress": project.get("progress"),
                "url": project.get("url"),
                "start_date": project.get("startDate"),
                "target_date": project.get("targetDate"),
                "teams": [
                    {
                        "name": team.get("name"),
                        "key": team.get("key"),
                    }
                    for team in (
                        project.get("teams", {}).get("nodes", [])
                    )
                ],
            }
            for project in raw_projects
        ]

        return {
            "user": viewer.get("name"),
            "count": len(projects),
            "projects": projects,
        }

    @tool
    def list_teams(limit: int = 30) -> dict:
        """
        List teams accessible to the authenticated Linear account.

        Use this when the user asks to show or list Linear teams.

        Args:
            limit: Maximum number of teams to return (1-100).
        """

        limit = max(1, min(limit, 100))

        viewer = get_viewer()

        data = make_request(
            """
            query Teams($limit: Int!) {
                teams(first: $limit) {
                    nodes {
                        id
                        name
                        key
                        description
                    }
                }
            }
            """,
            variables={
                "limit": limit,
            },
        )

        raw_teams = (
            data.get("teams", {}).get("nodes", [])
        )

        teams = [
            {
                "name": team.get("name"),
                "key": team.get("key"),
                "description": team.get("description"),
            }
            for team in raw_teams
        ]

        return {
            "user": viewer.get("name"),
            "count": len(teams),
            "teams": teams,
        }

    return [
        list_issues,
        list_projects,
        list_teams,
    ]
