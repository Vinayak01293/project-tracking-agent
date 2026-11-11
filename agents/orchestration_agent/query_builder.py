def generate_agent_query(intent: dict, target_user_name: str) -> str:

    platform = intent["platform"]
    operation = intent["operation"]
    filters = intent.get("filters") or {}

    operations = {
        ("github", "list_repositories"):
            "Retrieve the repositories accessible to the authenticated GitHub account.",

        ("github", "list_issues"):
            "Retrieve the GitHub issues associated with the authenticated account.",

        ("github", "list_pull_requests"):
            "Retrieve the pull requests authored by the authenticated GitHub account.",

        ("github", "list_starred_repositories"):
            "Retrieve repositories starred by the authenticated GitHub account.",

        ("linear", "list_issues"):
            "Retrieve issues assigned to the authenticated Linear user.",

        ("linear", "list_projects"):
            "Retrieve projects accessible to the authenticated Linear account.",

        ("linear", "list_teams"):
            "Retrieve teams accessible to the authenticated Linear account.",
    }

    instruction = operations.get((platform, operation))

    if not instruction:
        raise ValueError("Unsupported platform operation.")

    query = f"User: {target_user_name}. {instruction}"

    if filters:
        query += f" Apply these filters: {filters}."

    return query