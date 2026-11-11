import logging
from uuid import UUID

import httpx
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, SecretStr, model_validator

from core.models.users import (
    IntegrationProvider,
    User,
    UserIntegration,
)
from core.repository.user_repository import UserRepository
from core.security.encryption import (
    CredentialEncryptionError,
    credential_manager,
)

logger = logging.getLogger("platform")

router = APIRouter(
    prefix="/api/users",
    tags=["User Directory"],
)

user_repository = UserRepository()


# --------------------------------------------------
# Request Schemas
# --------------------------------------------------

class IntegrationCreateRequest(BaseModel):
    provider: IntegrationProvider = Field(
        description="Which Provider to Integrate"
    )
    secret: SecretStr = Field(
        description="Encrypted Secret like api-key/token")


class CreateUserRequest(BaseModel):
    name: str = Field(
        description="Name of the User",
        min_length=1, 
        max_length=100
    )
    email: EmailStr = Field(
        description="Email ID"
    )
    integrations: list[IntegrationCreateRequest] = Field(
        min_length=1,
        max_length=2,
    )

    @model_validator(mode="after")
    def validate_unique_providers(self):
        providers = [
            integration.provider
            for integration in self.integrations
        ]

        if len(providers) != len(set(providers)):
            raise ValueError(
                "Each integration provider can only be added once."
            )

        return self


# --------------------------------------------------
# Provider Credential Validation
# --------------------------------------------------

def validate_github_token(token: str) -> str:
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        response = httpx.get(
            "https://api.github.com/user",
            headers=headers,
            timeout=15,
        )

        if response.status_code == 401:
            raise HTTPException(
                status_code=400,
                detail="Invalid or expired GitHub token.",
            )

        if response.status_code == 403:
            raise HTTPException(
                status_code=400,
                detail="GitHub denied the request. Check token permissions or rate limits.",
            )

        response.raise_for_status()

        return response.json()["login"]

    except HTTPException:
        raise

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="GitHub API request timed out.",
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="Unable to connect to GitHub.",
        )

    except httpx.HTTPStatusError:
        raise HTTPException(
            status_code=502,
            detail="GitHub API returned an unexpected error.",
        )


def validate_linear_token(token: str) -> str:
    headers = {
        "Authorization": token,
        "Content-Type": "application/json",
    }

    query = """
        query {
            viewer {
                id
                name
                displayName
                email
            }
        }
    """

    try:
        response = httpx.post(
            "https://api.linear.app/graphql",
            headers=headers,
            json={"query": query},
            timeout=15,
        )

        if response.status_code in (401, 403):
            raise HTTPException(
                status_code=400,
                detail="Invalid Linear API key or insufficient permissions.",
            )

        response.raise_for_status()

        result = response.json()

        if result.get("errors"):
            raise HTTPException(
                status_code=400,
                detail="Linear API key validation failed.",
            )

        viewer = (result.get("data") or {}).get("viewer")

        if not viewer:
            raise HTTPException(
                status_code=400,
                detail="Unable to identify the Linear account.",
            )

        return (
            viewer.get("displayName")
            or viewer.get("name")
            or viewer.get("email")
        )

    except HTTPException:
        raise

    except httpx.TimeoutException:
        raise HTTPException(
            status_code=504,
            detail="Linear API request timed out.",
        )

    except httpx.RequestError:
        raise HTTPException(
            status_code=502,
            detail="Unable to connect to Linear.",
        )

    except httpx.HTTPStatusError:
        raise HTTPException(
            status_code=502,
            detail="Linear API returned an unexpected error.",
        )


# --------------------------------------------------
# Response Schemas
# --------------------------------------------------

class IntegrationResponse(BaseModel):
    provider: IntegrationProvider
    external_username: str
    is_active: bool


class UserResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    is_active: bool
    integrations: list[IntegrationResponse] = Field(
        default_factory=list
    )


def build_user_response(user: User) -> UserResponse:
    """
    Returns safe user metadata without exposing credentials.
    """

    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        is_active=user.is_active,
        integrations=[
            IntegrationResponse(
                provider=integration.provider,
                external_username=integration.external_username,
                is_active=integration.is_active,
            )
            for integration in user.integrations
        ],
    )


# --------------------------------------------------
# Create User with Integrations
# --------------------------------------------------

@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(request: CreateUserRequest):

    try:
        prepared_integrations = []

        for integration_request in request.integrations:
            provider = integration_request.provider
            secret = integration_request.secret.get_secret_value()

            if provider == IntegrationProvider.GITHUB:
                external_username = validate_github_token(secret)

            elif provider == IntegrationProvider.LINEAR:
                external_username = validate_linear_token(secret)

            else:
                raise HTTPException(
                    status_code=400,
                    detail="Unsupported integration provider.",
                )

            encrypted_secret = credential_manager.encrypt(secret)

            prepared_integrations.append(
                UserIntegration(
                    provider=provider,
                    external_username=external_username,
                    encrypted_secret=encrypted_secret,
                )
            )

        user = user_repository.create_user(
            name=request.name,
            email=str(request.email),
            integrations=prepared_integrations,
        )

        logger.info(
            "USER_CREATION_WITH_INTEGRATIONS_SUCCESS",
            extra={
                "user_id": str(user.id),
                "integration_providers": [
                    integration.provider.value
                    for integration in user.integrations
                ],
            },
        )

        return build_user_response(user)

    except HTTPException:
        raise

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    except CredentialEncryptionError:
        logger.exception("INTEGRATION_ENCRYPTION_FAILED")

        raise HTTPException(
            status_code=500,
            detail="Unable to secure integration credentials.",
        )

    except Exception:
        logger.exception("USER_CREATION_WITH_INTEGRATIONS_FAILED")

        raise HTTPException(
            status_code=500,
            detail="Unable to create user with integrations.",
        )
