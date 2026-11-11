
import logging

import httpx
from langchain_core.tools import tool

logger = logging.getLogger("github_agent")

GITHUB_API_BASE = "https://api.github.com"


class GitHubAPIError(Exception):
    pass


def create_github_tools(token: str, username: str):
    """
    Creates GitHub tools scoped to one registered user's credentials.

    The token and username are captured in the tool closures.
    The LLM cannot choose or override the authenticated identity.
    """

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    def make_request(endpoint: str, params: dict | None = None):
        url = f"{GITHUB_API_BASE}{endpoint}"

        try:
            response = httpx.get(
                url,
                headers=headers,
                params=params,
                timeout=20.0,
            )

            if response.status_code == 401:
                raise GitHubAPIError(
                    "GitHub authentication failed. "
                    "The stored integration token may be invalid."
                )

            if response.status_code == 403:
                raise GitHubAPIError(
                    "GitHub API access was denied. "
                    "Check token permissions or API rate limits."
                )

            if response.status_code == 404:
                raise GitHubAPIError(
                    "The requested GitHub resource was not found "
                    "or is not accessible to this account."
                )

            response.raise_for_status()
            return response.json()

        except httpx.TimeoutException:
            raise GitHubAPIError("GitHub API request timed out.")

        except httpx.HTTPStatusError as exc:
            logger.exception(
                "GITHUB_API_HTTP_ERROR",
                extra={
                    "status": exc.response.status_code,
                    "target_user": username,
                },
            )
            raise GitHubAPIError(
                f"GitHub API returned HTTP {exc.response.status_code}."
            )

        except httpx.RequestError:
            logger.exception(
                "GITHUB_API_CONNECTION_ERROR",
                extra={"target_user": username},
            )
            raise GitHubAPIError(
                "Unable to connect to the GitHub API."
            )

    @tool
    def list_repositories(
        limit: int = 30,
        sort: str = "updated",
    ) -> dict:
        """
        List repositories accessible to the selected GitHub user.

        Use this when the user asks to show, list, or summarize
        their GitHub repositories.

        Args:
            limit: Maximum number of repositories to return (1-100).
            sort: Repository sorting. One of created, updated,
                  pushed, or full_name.
        """
        limit = max(1, min(limit, 100))

        if sort not in {"created", "updated", "pushed", "full_name"}:
            sort = "updated"

        data = make_request(
            "/user/repos",
            params={
                "visibility": "all",
                "affiliation": "owner,collaborator,organization_member",
                "sort": sort,
                "per_page": limit,
                "page": 1,
            },
        )

        repositories = [
            {
                "name": repo["name"],
                "full_name": repo["full_name"],
                "description": repo.get("description"),
                "private": repo["private"],
                "language": repo.get("language"),
                "stars": repo["stargazers_count"],
                "forks": repo["forks_count"],
                "open_issues": repo["open_issues_count"],
                "url": repo["html_url"],
                "updated_at": repo["updated_at"],
            }
            for repo in data
        ]

        return {
            "user": username,
            "count": len(repositories),
            "repositories": repositories,
        }

    @tool
    def list_issues(
        state: str = "open",
        limit: int = 30,
    ) -> dict:
        """
        List issues associated with the authenticated GitHub user.

        Use this when the user asks about their GitHub issues.

        Args:
            state: Issue state: open, closed, or all.
            limit: Maximum number of issues to return (1-100).
        """
        if state not in {"open", "closed", "all"}:
            state = "open"

        limit = max(1, min(limit, 100))

        data = make_request(
            "/issues",
            params={
                "filter": "all",
                "state": state,
                "per_page": limit,
                "page": 1,
            },
        )

        issues = [
            {
                "number": issue["number"],
                "title": issue["title"],
                "state": issue["state"],
                "repository": issue["repository"]["full_name"],
                "url": issue["html_url"],
                "created_at": issue["created_at"],
                "updated_at": issue["updated_at"],
                "labels": [
                    label["name"] for label in issue.get("labels", [])
                ],
                "assignees": [
                    assignee["login"]
                    for assignee in issue.get("assignees", [])
                ],
            }
            for issue in data
            if "pull_request" not in issue
        ]

        return {
            "user": username,
            "count": len(issues),
            "issues": issues,
        }

    @tool
    def list_pull_requests(
        state: str = "open",
        limit: int = 30,
    ) -> dict:
        """
        List pull requests associated with the authenticated GitHub user.

        Use this when the user asks about their GitHub pull requests.

        Args:
            state: Pull request state: open, closed, or all.
            limit: Maximum number of pull requests to return (1-100).
        """
        if state not in {"open", "closed", "all"}:
            state = "open"

        limit = max(1, min(limit, 100))

        data = make_request(
            "/search/issues",
            params={
                "q": f"is:pr author:{username} state:{state}",
                "per_page": limit,
                "page": 1,
                "sort": "updated",
                "order": "desc",
            },
        )

        pull_requests = [
            {
                "number": pr["number"],
                "title": pr["title"],
                "state": pr["state"],
                "repository": pr["repository_url"].split("/repos/")[-1],
                "url": pr["html_url"],
                "created_at": pr["created_at"],
                "updated_at": pr["updated_at"],
                "labels": [
                    label["name"] for label in pr.get("labels", [])
                ],
                "comments": pr["comments"],
            }
            for pr in data.get("items", [])
        ]

        return {
            "user": username,
            "count": len(pull_requests),
            "pull_requests": pull_requests,
        }

    @tool
    def list_starred_repositories(limit: int = 30) -> dict:
        """
        List repositories starred by the authenticated GitHub user.

        Use this when the user asks about their starred repositories.

        Args:
            limit: Maximum number of repositories to return (1-100).
        """
        limit = max(1, min(limit, 100))

        data = make_request(
            "/user/starred",
            params={
                "per_page": limit,
                "page": 1,
            },
        )

        repositories = [
            {
                "name": repo["name"],
                "full_name": repo["full_name"],
                "description": repo.get("description"),
                "language": repo.get("language"),
                "stars": repo["stargazers_count"],
                "url": repo["html_url"],
            }
            for repo in data
        ]

        return {
            "user": username,
            "count": len(repositories),
            "repositories": repositories,
        }

    return [
        list_repositories,
        list_issues,
        list_pull_requests,
        list_starred_repositories,
    ]
