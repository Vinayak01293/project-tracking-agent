
import logging
import sys
from pathlib import Path

# Ensure backend is available on the Python import path.
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv

load_dotenv(BACKEND_DIR / ".env")

from agents.github_agent.github_agent import GitHubAgent
from core.repository.user_repository import UserRepository

logging.basicConfig(level=logging.INFO)

repository = UserRepository()
github_agent = GitHubAgent(repository)


def display_registered_users():
    users = repository.list_users()

    if not users:
        print("\nNo users registered.")
        return []

    print("\nRegistered users:")
    for index, user in enumerate(users, start=1):
        integration = repository.get_integration(
            user_id=str(user.id),
            provider="GITHUB",
        )

        github_status = (
            "Connected"
            if integration and integration.is_active
            else "Not connected"
        )

        print(
            f"{index}. {user.name} "
            f"({user.email}) - GitHub: {github_status}"
        )

    return users


def select_user(users):
    while True:
        try:
            choice = int(input("\nSelect user number: "))

            if 1 <= choice <= len(users):
                return users[choice - 1]

            print("Invalid selection.")

        except ValueError:
            print("Enter a valid number.")


def select_operation():
    operations = {
        "1": "Show my repositories",
        "2": "Show my open issues",
        "3": "Show my open pull requests",
        "4": "Show my starred repositories",
        "5": "Custom query",
    }

    print("\nSelect operation:")
    for key, value in operations.items():
        print(f"{key}. {value}")

    while True:
        choice = input("\nEnter choice: ").strip()

        if choice in operations:
            return choice

        print("Invalid selection.")


def get_query(choice, username):
    queries = {
        "1": f"List the repositories belonging to or accessible by {username}.",
        "2": "Show my open GitHub issues.",
        "3": "Show my open GitHub pull requests.",
        "4": "Show my starred repositories.",
    }

    if choice == "5":
        return input("\nEnter your GitHub query: ").strip()

    return queries[choice]


def run_test():
    print("=" * 60)
    print("GITHUB AGENT TEST")
    print("=" * 60)

    users = display_registered_users()

    if not users:
        return

    user = select_user(users)

    integration = repository.get_integration(
        user_id=str(user.id),
        provider="GITHUB",
    )

    if not integration or not integration.is_active:
        print(f"\n{user.name} does not have an active GitHub integration.")
        return

    print(f"\nSelected user: {user.name}")
    print(f"GitHub account: {integration.external_username}")

    choice = select_operation()
    query = get_query(choice, integration.external_username)

    if not query:
        print("Query cannot be empty.")
        return

    print("\n" + "=" * 60)
    print("EXECUTING GITHUB AGENT")
    print("=" * 60)
    print(f"User: {user.name}")
    print(f"Query: {query}")

    result = github_agent.invoke(
        user_id=str(user.id),
        query=query,
    )

    print("\n" + "=" * 60)
    print("AGENT RESPONSE")
    print("=" * 60)

    if result["success"]:
        print("Status: SUCCESS")
        print(f"Platform: {result['platform']}")
        print(f"User: {result['user']}")
        print(f"\n{result['response']}")
    else:
        print("Status: FAILED")
        print(result["response"])

    print("\n" + "=" * 60)


if __name__ == "__main__":
    run_test()