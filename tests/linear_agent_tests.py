import logging
import sys
from pathlib import Path

# Load environment variables before importing application modules.
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv

load_dotenv(BACKEND_DIR / ".env")

load_dotenv()

from agents.linear_agent.linear_agent import LinearAgent
from core.models.users import IntegrationProvider
from core.repository.user_repository import UserRepository

logging.basicConfig(level=logging.INFO)

def select_user():
    """Display registered users with active Linear integrations."""

    repository = UserRepository()
    users = repository.list_users()

    linear_users = [
        user
        for user in users
        if repository.get_integration(
            user_id=user.id,
            provider=IntegrationProvider.LINEAR,
        )
    ]

    if not linear_users:
        print("\nNo users with active Linear integrations found.")
        return None

    print("\n========== REGISTERED LINEAR USERS ==========")

    for index, user in enumerate(linear_users, start=1):
        print(f"{index}. {user.name} ({user.email})")

    while True:
        try:
            selection = int(input("\nSelect a user: "))

            if 1 <= selection <= len(linear_users):
                return linear_users[selection - 1]

            print("Invalid selection. Try again.")

        except ValueError:
            print("Please enter a valid number.")


def select_operation():
    """Allow the tester to choose a Linear operation."""

    operations = {
        "1": (
            "List my open Linear issues",
            "Show my open Linear issues",
        ),
        "2": (
            "List my completed Linear issues",
            "Show my completed Linear issues",
        ),
        "3": (
            "List Linear projects",
            "Show my Linear projects",
        ),
        "4": (
            "List Linear teams",
            "Show my Linear teams",
        ),
        "5": (
            "Custom query",
            None,
        ),
    }

    print("\n========== LINEAR OPERATIONS ==========")

    for key, (label, _) in operations.items():
        print(f"{key}. {label}")

    while True:
        choice = input("\nSelect an operation: ").strip()

        if choice not in operations:
            print("Invalid selection. Try again.")
            continue

        if choice == "5":
            query = input("\nEnter your Linear query: ").strip()

            if not query:
                print("Query cannot be empty.")
                continue

            return query

        return operations[choice][1]


def main():
    print("\n==========================================")
    print("       LINEAR AGENT TEST APPLICATION")
    print("==========================================")

    # 1. Select registered user.
    user = select_user()

    if not user:
        return

    print(f"\nSelected user: {user.name}")

    # 2. Select operation.
    query = select_operation()

    if not query:
        return

    print("\n==========================================")
    print("             AGENT EXECUTION")
    print("==========================================")
    print(f"User  : {user.name}")
    print(f"Query : {query}")

    # 3. Initialize and invoke Linear Agent.
    try:
        agent = LinearAgent()

        result = agent.invoke(
            user_id=str(user.id),
            query=query,
        )

        # 4. Display result.
        print("\n==========================================")
        print("              AGENT RESPONSE")
        print("==========================================")

        print(f"Status   : {'SUCCESS' if result.get('success') else 'FAILED'}")
        print(f"Platform : {result.get('platform')}")
        print(f"User     : {result.get('user', user.name)}")

        print("\nResponse:")
        print("------------------------------------------")
        print(result.get("response"))
        print("------------------------------------------")

    except Exception as exc:
        print("\nLINEAR AGENT EXECUTION FAILED")
        print(f"Error: {exc}")


if __name__ == "__main__":
    main()
