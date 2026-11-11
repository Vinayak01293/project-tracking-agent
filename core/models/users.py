
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field


class IntegrationProvider(str, Enum):
    GITHUB = "GITHUB"
    LINEAR = "LINEAR"


class UserIntegration(BaseModel):
    provider: IntegrationProvider
    external_username: str
    encrypted_secret: str
    is_active: bool = True


class User(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    name: str
    email: EmailStr
    is_active: bool = True
    integrations: list[UserIntegration] = Field(default_factory=list)
