"""Recoverable encryption primitive; no persistence, vault, or automatic restoration.

Ciphertext includes the 16-byte authentication tag. Callers must supply their
expected key ID and purpose on decryption, rather than trust envelope metadata.
"""

import base64
import binascii
from dataclasses import dataclass
import json
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESCCM


class EncryptionConfigurationError(ValueError):
    """The environment does not contain a valid encryption key."""


@dataclass(frozen=True)
class EncryptedData:
    key_id: str
    purpose: str
    nonce: bytes
    ciphertext: bytes


def _key() -> bytes:
    encoded = os.environ.get("AEGIS_VAULT_KEY")
    if not encoded:
        raise EncryptionConfigurationError("AEGIS_VAULT_KEY is required")
    try:
        key = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error):
        raise EncryptionConfigurationError("AEGIS_VAULT_KEY must be base64 encoding 32 bytes") from None
    if len(key) != 32:
        raise EncryptionConfigurationError("AEGIS_VAULT_KEY must encode exactly 32 bytes")
    return key


def _aad(key_id: str, purpose: str) -> bytes:
    if not isinstance(key_id, str) or not key_id or not isinstance(purpose, str) or not purpose:
        raise ValueError("Nonempty key ID and purpose are required")
    return json.dumps(["AEGIS-AES-256-CCM-v1", key_id, purpose],
                      ensure_ascii=True, separators=(",", ":")).encode("ascii")


def encrypt(plaintext: bytes, *, key_id: str, purpose: str) -> EncryptedData:
    """Encrypt at most 65,535 bytes with a fresh 13-byte nonce and 16-byte tag."""
    cipher = AESCCM(_key(), tag_length=16)
    aad = _aad(key_id, purpose)
    if not isinstance(plaintext, bytes):
        raise TypeError("Plaintext must be bytes")
    if len(plaintext) > 65535:
        raise ValueError("Plaintext exceeds the 13-byte CCM nonce capacity")
    nonce = os.urandom(13)
    return EncryptedData(key_id, purpose, nonce, cipher.encrypt(nonce, plaintext, aad))


def decrypt(data: EncryptedData, *, key_id: str, purpose: str) -> bytes:
    """Authenticate fully before releasing plaintext; InvalidTag rejects tampering."""
    cipher = AESCCM(_key(), tag_length=16)
    aad = _aad(key_id, purpose)
    if data.key_id != key_id or data.purpose != purpose:
        raise InvalidTag("Encryption context mismatch")
    if not isinstance(data.nonce, bytes) or len(data.nonce) != 13:
        raise ValueError("A 13-byte nonce is required")
    if not isinstance(data.ciphertext, bytes) or len(data.ciphertext) < 16:
        raise ValueError("Ciphertext must include a 16-byte authentication tag")
    return cipher.decrypt(data.nonce, data.ciphertext, aad)
