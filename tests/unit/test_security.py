"""
Unit tests for security utilities (JWT, password hashing).
"""
import pytest
from jose import JWTError

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


@pytest.mark.unit
class TestPasswordHashing:
    def test_hash_password_returns_different_string(self):
        plain = "MyP@ssword1"
        hashed = hash_password(plain)
        assert hashed != plain

    def test_verify_password_correct(self):
        plain = "MyP@ssword1"
        hashed = hash_password(plain)
        assert verify_password(plain, hashed) is True

    def test_verify_password_wrong(self):
        hashed = hash_password("CorrectP@ss1")
        assert verify_password("WrongP@ss1", hashed) is False

    def test_two_hashes_of_same_password_differ(self):
        """Bcrypt uses salt — same password produces different hashes."""
        plain = "MyP@ssword1"
        assert hash_password(plain) != hash_password(plain)


@pytest.mark.unit
class TestJWT:
    def test_access_token_decodes_correctly(self):
        token = create_access_token(subject="user-uuid-123")
        payload = decode_token(token)
        assert payload["sub"] == "user-uuid-123"
        assert payload["type"] == "access"

    def test_refresh_token_type_is_refresh(self):
        token = create_refresh_token(subject="user-uuid-456")
        payload = decode_token(token)
        assert payload["type"] == "refresh"

    def test_invalid_token_raises_jwterror(self):
        with pytest.raises(JWTError):
            decode_token("this.is.not.a.valid.token")

    def test_tampered_token_raises_jwterror(self):
        token = create_access_token(subject="user-uuid-789")
        tampered = token[:-5] + "XXXXX"
        with pytest.raises(JWTError):
            decode_token(tampered)

    def test_access_token_contains_extra_claims(self):
        token = create_access_token(subject="uid-1", extra_claims={"role": "admin"})
        payload = decode_token(token)
        assert payload["role"] == "admin"
