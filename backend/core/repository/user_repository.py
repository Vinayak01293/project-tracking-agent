
import json
import logging
import threading
from pathlib import Path
from uuid import UUID

from core.models.users import (
    IntegrationProvider,
    User,
    UserIntegration,
    UserRole,
)

logger = logging.getLogger("platform")


class UserRepository:
    """
    JSON-based repository for application users and integrations.
    """

    def __init__(self, file_path: Path | None = None):
        self.file_path = file_path or (
            Path(__file__).resolve().parents[2]
            / "data"
            / "users.json"
        )

        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        self._lock = threading.RLock()

        if not self.file_path.exists():
            self._write_data({"users": []})

    # --------------------------------------------------
    # Internal JSON Operations
    # --------------------------------------------------

    def _read_data(self) -> dict:
        try:
            with self.file_path.open("r", encoding="utf-8") as file:
                data = json.load(file)

            if not isinstance(data, dict) or not isinstance(
                data.get("users"), list
            ):
                raise ValueError("Invalid user directory JSON structure.")

            return data

        except (json.JSONDecodeError, OSError, ValueError):
            logger.exception("USER_DIRECTORY_READ_FAILED")
            raise

    def _write_data(self, data: dict) -> None:
        temporary_file = self.file_path.with_suffix(".tmp")

        try:
            with temporary_file.open("w", encoding="utf-8") as file:
                json.dump(data, file, indent=4, ensure_ascii=False)

            temporary_file.replace(self.file_path)

        except Exception:
            logger.exception("USER_DIRECTORY_WRITE_FAILED")
            raise

    # --------------------------------------------------
    # User Operations
    # --------------------------------------------------

    def create_user(
        self,
        name: str,
        email: str,
        role: UserRole = UserRole.USER,
    ) -> User:

        with self._lock:
            data = self._read_data()

            normalized_email = str(email).strip().lower()

            for existing in data["users"]:
                if existing["email"].lower() == normalized_email:
                    raise ValueError(
                        f"User with email {normalized_email} already exists."
                    )

            user = User(
                name=name.strip(),
                email=normalized_email,
                role=role,
            )

            data["users"].append(
                user.model_dump(mode="json")
            )

            self._write_data(data)

            logger.info(
                "USER_CREATED",
                extra={"user_id": str(user.id), "role": user.role.value},
            )

            return user

    def get_user_by_id(self, user_id: UUID | str) -> User | None:

        with self._lock:
            data = self._read_data()

            for item in data["users"]:
                if item["id"] == str(user_id):
                    return User.model_validate(item)

            return None

    def get_user_by_email(self, email: str) -> User | None:

        normalized_email = email.strip().lower()

        with self._lock:
            data = self._read_data()

            for item in data["users"]:
                if item["email"].lower() == normalized_email:
                    return User.model_validate(item)

            return None

    def list_users(
        self,
        include_inactive: bool = False,
    ) -> list[User]:

        with self._lock:
            data = self._read_data()

            users = [
                User.model_validate(item)
                for item in data["users"]
            ]

            if not include_inactive:
                users = [
                    user for user in users if user.is_active
                ]

            return users

    # --------------------------------------------------
    # Integration Operations
    # --------------------------------------------------

    def add_integration(
        self,
        user_id: UUID | str,
        provider: IntegrationProvider,
        external_username: str,
        encrypted_secret: str,
    ) -> User:

        with self._lock:
            data = self._read_data()

            user_data = next(
                (
                    item for item in data["users"]
                    if item["id"] == str(user_id)
                ),
                None,
            )

            if not user_data:
                raise ValueError("User does not exist.")

            if not user_data["is_active"]:
                raise ValueError("Cannot add integration to inactive user.")

            integration = UserIntegration(
                provider=provider,
                external_username=external_username.strip(),
                encrypted_secret=encrypted_secret,
            )

            existing_index = next(
                (
                    index for index, item
                    in enumerate(user_data["integrations"])
                    if item["provider"] == provider.value
                ),
                None,
            )

            if existing_index is not None:
                user_data["integrations"][existing_index] = (
                    integration.model_dump(mode="json")
                )
            else:
                user_data["integrations"].append(
                    integration.model_dump(mode="json")
                )

            self._write_data(data)

            logger.info(
                "USER_INTEGRATION_SAVED",
                extra={
                    "user_id": str(user_id),
                    "provider": provider.value,
                },
            )

            return User.model_validate(user_data)

    def get_integration(
        self,
        user_id: UUID | str,
        provider: IntegrationProvider,
    ) -> UserIntegration | None:

        user = self.get_user_by_id(user_id)

        if not user or not user.is_active:
            return None

        for integration in user.integrations:
            if (
                integration.provider == provider
                and integration.is_active
            ):
                return integration

        return None
