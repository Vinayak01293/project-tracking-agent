
import logging
from uuid import UUID

from core.models.users import (
    IntegrationProvider,
    User,
    UserRole,
)
from core.repository.user_repository import UserRepository
from core.security.encryption import (
    CredentialEncryptionError,
    credential_manager,
)
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field, SecretStr

logger = logging.getLogger("platform")

router = APIRouter(
    prefix="/api/users",
    tags=["User Directory"],
)

user_repository = UserRepository()


# --------------------------------------------------
# Request Schemas
# --------------------------------------------------

class CreateUserRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    role: UserRole = UserRole.USER


class CreateIntegrationRequest(BaseModel):
    provider: IntegrationProvider
    external_username: str = Field(min_length=1, max_length=255)
    secret: SecretStr


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
    role: UserRole
    is_active: bool
    integrations: list[IntegrationResponse] = Field(default_factory=list)


def build_user_response(user: User) -> UserResponse:
    """
    Converts a User into a safe API response.
    Encrypted credentials are deliberately excluded.
    """

    return UserResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role,
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
# Create User
# --------------------------------------------------

@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user(request: CreateUserRequest):

    try:
        user = user_repository.create_user(
            name=request.name,
            email=str(request.email),
            role=request.role,
        )

        logger.info(
            "USER_CREATION_API_SUCCESS",
            extra={"user_id": str(user.id)},
        )

        return build_user_response(user)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        )

    except Exception:
        logger.exception("USER_CREATION_API_FAILED")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to create user.",
        )


# --------------------------------------------------
# Add / Update User Integration
# --------------------------------------------------

@router.post(
    "/{user_id}/integrations",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
)
def add_user_integration(
    user_id: UUID,
    request: CreateIntegrationRequest,
):

    try:
        # Encrypt the credential before persistence.
        encrypted_secret = credential_manager.encrypt(
            request.secret.get_secret_value()
        )

        user = user_repository.add_integration(
            user_id=user_id,
            provider=request.provider,
            external_username=request.external_username,
            encrypted_secret=encrypted_secret,
        )

        logger.info(
            "INTEGRATION_CREATION_API_SUCCESS",
            extra={
                "user_id": str(user_id),
                "provider": request.provider.value,
            },
        )

        return build_user_response(user)

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    except CredentialEncryptionError:
        logger.exception("INTEGRATION_ENCRYPTION_FAILED")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to secure integration credentials.",
        )

    except Exception:
        logger.exception("INTEGRATION_CREATION_API_FAILED")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save integration.",
        )
