"""
encryption_layer.py  --  Privacy & Cryptography layer (runs AFTER Laya's decision)

Primitives
  * AES-256-GCM  : confidentiality + integrity (authenticated encryption)
  * HKDF-SHA256  : derive separate sub-keys from one master key
  * HMAC-SHA256  : keyed fingerprints / pseudonymous IDs (and SHA-256 for file integrity)
  * Argon2id     : password hashing ONLY

Flow
  Laya says "sensitive"  ->  protect_text()  ->  (masked_text, vault_records)
      masked_text   : safe to send to the LLM / logs   e.g. "call [PHONE_1]"
      vault_records : AES-GCM encrypted originals, store in DB
  Later, if the user is authorised -> restore_text()

Run this file directly to execute the self-tests.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import re
from dataclasses import dataclass

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode("ascii")


def _b64d(s: str) -> bytes:
    return base64.urlsafe_b64decode(s.encode("ascii"))


class CryptoError(Exception):
    """Raised for ANY decryption/format failure. Never includes plaintext or keys."""


# --------------------------------------------------------------------------- #
# 1. Key management
# --------------------------------------------------------------------------- #
def generate_master_key() -> str:
    """Create a new 256-bit master key (base64). Do this ONCE, store as a secret."""
    return _b64e(AESGCM.generate_key(bit_length=256))


class KeyManager:
    """
    Holds a keyring {key_id: master_key_bytes}. The newest key (current_kid) encrypts;
    any key in the ring can decrypt -> this gives you key rotation.

    Load from env / Kaggle Secrets, e.g.
        LEAK_GW_KEYS='{"k1": "<base64 32 bytes>"}'
        LEAK_GW_CURRENT_KID='k1'
    """

    def __init__(self, keyring: dict[str, str], current_kid: str):
        if current_kid not in keyring:
            raise ValueError("current_kid not in keyring")
        self._ring: dict[str, bytes] = {}
        for kid, k in keyring.items():
            raw = _b64d(k)
            if len(raw) != 32:
                raise ValueError(f"key {kid!r} must be exactly 32 bytes (AES-256)")
            self._ring[kid] = raw
        self.current_kid = current_kid
        self._subkeys: dict[tuple[str, bytes], bytes] = {}

    @classmethod
    def from_env(cls) -> "KeyManager":
        keys = os.environ.get("LEAK_GW_KEYS")
        kid = os.environ.get("LEAK_GW_CURRENT_KID")
        if not keys or not kid:
            raise RuntimeError("Set LEAK_GW_KEYS and LEAK_GW_CURRENT_KID (fail closed).")
        return cls(json.loads(keys), kid)

    def subkey(self, kid: str, purpose: bytes) -> bytes:
        """HKDF: one master key -> independent keys for 'enc' and 'hmac'."""
        cached = self._subkeys.get((kid, purpose))
        if cached is not None:
            return cached
        master = self._ring.get(kid)
        if master is None:
            raise CryptoError("unknown key id")
        key = HKDF(
            algorithm=hashes.SHA256(), length=32, salt=None, info=b"leakgw/v1/" + purpose
        ).derive(master)
        self._subkeys[(kid, purpose)] = key
        return key


# --------------------------------------------------------------------------- #
# 2. AES-256-GCM
# --------------------------------------------------------------------------- #
class AesGcmService:
    NONCE_BYTES = 12  # 96-bit random nonce, the GCM standard

    def __init__(self, keys: KeyManager):
        self.keys = keys

    def encrypt(self, plaintext: str, aad: str = "") -> dict:
        """
        aad = context that must match at decrypt time (e.g. "user:42|req:abc|tag:PHONE").
        It is authenticated but not encrypted, so a ciphertext can't be replayed elsewhere.
        """
        kid = self.keys.current_kid
        nonce = os.urandom(self.NONCE_BYTES)  # fresh per encryption, never reused
        ct = AESGCM(self.keys.subkey(kid, b"enc")).encrypt(
            nonce, plaintext.encode("utf-8"), aad.encode("utf-8")
        )  # ct = ciphertext || 16-byte auth tag
        return {"v": 1, "alg": "AES-256-GCM", "kid": kid, "nonce": _b64e(nonce), "ct": _b64e(ct)}

    def decrypt(self, envelope: dict, aad: str = "") -> str:
        try:
            if envelope.get("v") != 1 or envelope.get("alg") != "AES-256-GCM":
                raise CryptoError("unsupported envelope")
            key = self.keys.subkey(envelope["kid"], b"enc")
            pt = AESGCM(key).decrypt(
                _b64d(envelope["nonce"]), _b64d(envelope["ct"]), aad.encode("utf-8")
            )
            return pt.decode("utf-8")
        except (InvalidTag, KeyError, ValueError, TypeError, AttributeError):
            # Tampered data, wrong key, wrong AAD, malformed envelope -> same generic error
            raise CryptoError("decryption failed") from None


# --------------------------------------------------------------------------- #
# 3. Hashing (SHA-256 / HMAC-SHA256)
# --------------------------------------------------------------------------- #
def sha256_hex(data: bytes) -> str:
    """Plain SHA-256: integrity checksums of files/configs/datasets. NOT for secrets/PII."""
    return hashlib.sha256(data).hexdigest()


class Fingerprinter:
    """HMAC-SHA256: stable pseudonymous ID for a value (e.g. to detect repeated phone
    numbers in audit logs without storing them). Plain SHA-256 of a phone number can be
    brute-forced; the secret key prevents that."""

    def __init__(self, keys: KeyManager):
        self.keys = keys

    def fingerprint(self, value: str) -> str:
        key = self.keys.subkey(self.keys.current_kid, b"hmac")
        return hmac.new(key, value.encode("utf-8"), hashlib.sha256).hexdigest()


# --------------------------------------------------------------------------- #
# 4. Passwords (Argon2id)  -- only if your gateway has its own login
# --------------------------------------------------------------------------- #
_ph = PasswordHasher()  # argon2-cffi defaults to Argon2id; salt is generated + embedded


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(stored_hash: str, password: str) -> bool:
    try:
        return _ph.verify(stored_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_needs_rehash(stored_hash: str) -> bool:
    return _ph.check_needs_rehash(stored_hash)


# --------------------------------------------------------------------------- #
# 5. Token vault: protect sensitive spans, restore only when authorised
# --------------------------------------------------------------------------- #
@dataclass
class Span:
    start: int
    end: int
    label: str  # e.g. "PHONE", "AADHAAR", "EMAIL"


class TokenVault:
    def __init__(self, aes: AesGcmService, fp: Fingerprinter):
        self.aes, self.fp = aes, fp

    def protect_text(self, text: str, spans: list[Span], *, user_id: str, request_id: str,
                     label_prefix: str = ""):
        """
        Replace each span with [LABEL_n] and return encrypted originals.
        Returns (masked_text, records). Store `records` in your DB; never log `text`.
        """
        spans = sorted(spans, key=lambda s: s.start)
        prev_end = 0
        for s in spans:  # validate offsets (fail closed on bad input)
            if not (0 <= s.start < s.end <= len(text)) or s.start < prev_end:
                raise ValueError("invalid or overlapping span")
            prev_end = s.end

        out, cursor, counters, records = [], 0, {}, []
        for s in spans:
            counters[s.label] = counters.get(s.label, 0) + 1
            token = f"[{label_prefix}{s.label}_{counters[s.label]}]"
            original = text[s.start:s.end]
            aad = f"user:{user_id}|req:{request_id}|tok:{token}"
            records.append(
                {
                    "token": token,
                    "label": s.label,
                    "fingerprint": self.fp.fingerprint(original),
                    "envelope": self.aes.encrypt(original, aad),
                }
            )
            out.append(text[cursor:s.start])
            out.append(token)
            cursor = s.end
        out.append(text[cursor:])
        return "".join(out), records

    def restore_text(self, masked_text: str, records: list[dict], *, user_id: str,
                     request_id: str, authorized: bool) -> str:
        if not authorized:  # authorisation check always wins
            return masked_text
        plain = {}
        for r in records:  # decrypt everything first: any failure aborts before output is built
            aad = f"user:{user_id}|req:{request_id}|tok:{r['token']}"
            plain[r["token"]] = self.aes.decrypt(r["envelope"], aad)
        if not plain:
            return masked_text
        pattern = re.compile("|".join(re.escape(t) for t in sorted(plain, key=len, reverse=True)))
        return pattern.sub(lambda m: plain[m.group(0)], masked_text)

    def protect_whole(self, text: str, *, user_id: str, request_id: str) -> dict:
        """Fallback when Laya gives a sentence-level label but no spans."""
        return self.aes.encrypt(text, f"user:{user_id}|req:{request_id}|whole")


# --------------------------------------------------------------------------- #
# Self-tests:  python encryption_layer.py
# --------------------------------------------------------------------------- #
def _self_test() -> None:
    km = KeyManager({"k1": generate_master_key()}, "k1")
    aes, fp = AesGcmService(km), Fingerprinter(km)

    # round trip
    env = aes.encrypt("9876543210", aad="ctx")
    assert aes.decrypt(env, aad="ctx") == "9876543210"

    # nonce uniqueness
    assert aes.encrypt("x")["nonce"] != aes.encrypt("x")["nonce"]

    # tamper -> rejected
    bad = dict(env)
    raw = bytearray(_b64d(bad["ct"]))
    raw[0] ^= 1
    bad["ct"] = _b64e(bytes(raw))
    try:
        aes.decrypt(bad, aad="ctx")
        raise AssertionError("tamper not detected")
    except CryptoError:
        pass

    # wrong AAD -> rejected
    try:
        aes.decrypt(env, aad="other")
        raise AssertionError("AAD not enforced")
    except CryptoError:
        pass

    # key rotation: old ciphertext still readable after adding k2
    km2 = KeyManager({"k1": _b64e(km._ring["k1"]), "k2": generate_master_key()}, "k2")
    assert AesGcmService(km2).decrypt(env, aad="ctx") == "9876543210"

    # fingerprint is deterministic and not plain sha256
    assert fp.fingerprint("a") == fp.fingerprint("a") != sha256_hex(b"a")

    # passwords
    h = hash_password("Correct#Horse9")
    assert verify_password(h, "Correct#Horse9") and not verify_password(h, "wrong")

    # vault
    vault = TokenVault(aes, fp)
    text = "Call me on 9876543210 or mail a@b.com"
    m = re.search(r"9876543210", text)
    e = re.search(r"a@b\.com", text)
    masked, recs = vault.protect_text(
        text, [Span(m.start(), m.end(), "PHONE"), Span(e.start(), e.end(), "EMAIL")],
        user_id="u1", request_id="r1",
    )
    assert masked == "Call me on [PHONE_1] or mail [EMAIL_1]", masked
    assert "9876543210" not in json.dumps(recs)
    assert vault.restore_text(masked, recs, user_id="u1", request_id="r1", authorized=True) == text
    assert vault.restore_text(masked, recs, user_id="u1", request_id="r1", authorized=False) == masked
    try:  # another user cannot restore
        vault.restore_text(masked, recs, user_id="u2", request_id="r1", authorized=True)
        raise AssertionError("cross-user restore allowed")
    except CryptoError:
        pass

    print("All encryption-layer self-tests passed.")


if __name__ == "__main__":
    _self_test()
