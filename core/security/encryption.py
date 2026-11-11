
import logging
import os

from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("platform")


class CredentialEncryptionError(Exception):
    """Raised when credential encryption or decryption fails."""


class CredentialManager:
    """
    Handles encryption and decryption of external platform
    credentials using Fernet symmetric encryption.
    """

    def __init__(self):
        encryption_key = os.getenv("FERNET_KEY")

        if not encryption_key:
            raise RuntimeError(
                "FERNET_KEY environment variable is not configured."
            )

        try:
            self.cipher = Fernet(encryption_key.encode("utf-8"))

        except (ValueError, TypeError):
            raise RuntimeError(
                "FERNET_KEY is invalid. Generate a valid Fernet key."
            )

    def encrypt(self, secret: str) -> str:
        """
        Encrypts a plaintext API key or Personal Access Token.

        Returns:
            Encrypted credential as a string.
        """

        if not secret or not secret.strip():
            raise ValueError("Cannot encrypt an empty credential.")

        try:
            encrypted = self.cipher.encrypt(
                secret.encode("utf-8")
            )

            logger.info("CREDENTIAL_ENCRYPTION_SUCCESSFUL")

            return encrypted.decode("utf-8")

        except Exception as exc:
            logger.exception("CREDENTIAL_ENCRYPTION_FAILED")

            raise CredentialEncryptionError(
                "Failed to encrypt credential."
            ) from exc

    def decrypt(self, encrypted_secret: str) -> str:
        """
        Decrypts a stored credential.

        Returns:
            Original plaintext credential.
        """

        if not encrypted_secret:
            raise ValueError("Encrypted credential cannot be empty.")

        try:
            decrypted = self.cipher.decrypt(
                encrypted_secret.encode("utf-8")
            )

            logger.info("CREDENTIAL_DECRYPTION_SUCCESSFUL")

            return decrypted.decode("utf-8")

        except InvalidToken as exc:
            logger.error("CREDENTIAL_DECRYPTION_FAILED_INVALID_TOKEN")

            raise CredentialEncryptionError(
                "Credential decryption failed. "
                "Check the encryption key or stored ciphertext."
            ) from exc

        except Exception as exc:
            logger.exception("CREDENTIAL_DECRYPTION_FAILED")

            raise CredentialEncryptionError(
                "Failed to decrypt credential."
            ) from exc


# ---------------------------------------------------------
# Shared Credential Manager
# ---------------------------------------------------------

credential_manager = CredentialManager()
