import base64
from dataclasses import replace

from cryptography.exceptions import InvalidTag
import pytest

from backend.encryption import EncryptionConfigurationError, decrypt, encrypt


@pytest.fixture(autouse=True)
def synthetic_key(monkeypatch):
    monkeypatch.setenv("AEGIS_VAULT_KEY", base64.b64encode(bytes(range(32))).decode("ascii"))


def seal(value=b"synthetic confidential record"):
    return encrypt(value, key_id="test-key-1", purpose="confidential-record")


def open_record(data, **kwargs):
    return decrypt(data, key_id=kwargs.get("key_id", "test-key-1"),
                   purpose=kwargs.get("purpose", "confidential-record"))


@pytest.mark.parametrize("plaintext", [b"", b"synthetic record", "synthetic multilingual नमस्ते".encode(), b"x" * 65535], ids=["empty", "record", "unicode", "maximum-size"])
def test_round_trip_and_sizes(plaintext):
    data = seal(plaintext)
    assert open_record(data) == plaintext
    assert len(data.nonce) == 13
    assert len(data.ciphertext) == len(plaintext) + 16


def test_fresh_nonce():
    first, second = seal(), seal()
    assert first.nonce != second.nonce
    assert first.ciphertext != second.ciphertext


@pytest.mark.parametrize("field", ["ciphertext", "tag", "nonce", "key_id", "purpose"])
def test_tamper_rejected(field):
    data = seal()
    if field in ("key_id", "purpose"):
        changed = replace(data, **{field: "tampered"})
    else:
        attr = "ciphertext" if field == "tag" else field
        value = bytearray(getattr(data, attr))
        value[-1 if field == "tag" else 0] ^= 1
        changed = replace(data, **{attr: bytes(value)})
    with pytest.raises(InvalidTag):
        open_record(changed)


def test_wrong_key(monkeypatch):
    data = seal()
    monkeypatch.setenv("AEGIS_VAULT_KEY", base64.b64encode(b"z" * 32).decode("ascii"))
    with pytest.raises(InvalidTag):
        open_record(data)


@pytest.mark.parametrize("field", ["key_id", "purpose"])
def test_wrong_expected_context(field):
    with pytest.raises(InvalidTag):
        open_record(seal(), **{field: "wrong-context"})


@pytest.mark.parametrize("field", ["key_id", "purpose"])
def test_metadata_is_authenticated_even_if_caller_accepts_change(field):
    data = replace(seal(), **{field: "different"})
    with pytest.raises(InvalidTag):
        open_record(data, **{field: "different"})


@pytest.mark.parametrize("encoded", [None, "", "not-base64!", "é", base64.b64encode(b"a" * 31).decode(), base64.b64encode(b"a" * 33).decode()])
def test_missing_or_invalid_key_fails_closed(monkeypatch, encoded):
    data = seal()
    if encoded is None:
        monkeypatch.delenv("AEGIS_VAULT_KEY")
    else:
        monkeypatch.setenv("AEGIS_VAULT_KEY", encoded)
    for operation in (seal, lambda: open_record(data)):
        with pytest.raises(EncryptionConfigurationError) as error:
            operation()
        if encoded:
            assert encoded not in str(error.value)


def test_capacity_bound():
    with pytest.raises(ValueError):
        seal(b"x" * 65536)


@pytest.mark.parametrize("nonce", [b"", b"x" * 12, b"x" * 14])
def test_nonce_length_rejected(nonce):
    with pytest.raises(ValueError):
        open_record(replace(seal(), nonce=nonce))


def test_truncated_tag_rejected():
    with pytest.raises(ValueError):
        open_record(replace(seal(), ciphertext=b"x" * 15))


@pytest.mark.parametrize("context", [{"key_id": "", "purpose": "record"}, {"key_id": "key", "purpose": ""}])
def test_empty_context_rejected(context):
    with pytest.raises(ValueError):
        encrypt(b"synthetic", **context)
