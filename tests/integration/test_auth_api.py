"""
Integration tests for Auth API endpoints.

These tests use the full FastAPI app with an in-memory SQLite database.
They verify the complete request → middleware → route → service → repository → response cycle.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestAuthRegisterEndpoint:
    @pytest.mark.asyncio
    async def test_register_returns_201(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "integration@example.com",
                "password": "Strong@123",
                "first_name": "Integration",
                "last_name": "Test",
                "default_currency": "USD",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["email"] == "integration@example.com"
        assert "id" in data
        assert "hashed_password" not in data  # Never leak password hash

    @pytest.mark.asyncio
    async def test_register_duplicate_email_returns_409(self, async_client: AsyncClient):
        payload = {
            "email": "duplicate@example.com",
            "password": "Strong@123",
            "first_name": "Dup",
            "last_name": "User",
        }
        await async_client.post("/api/v1/auth/register", json=payload)
        response = await async_client.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 409
        assert response.json()["error"]["code"] == "CONFLICT"

    @pytest.mark.asyncio
    async def test_register_invalid_email_returns_422(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "not-an-email",
                "password": "Strong@123",
                "first_name": "A",
                "last_name": "B",
            },
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_weak_password_returns_422(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "weak@example.com",
                "password": "password",
                "first_name": "A",
                "last_name": "B",
            },
        )
        assert response.status_code == 422


@pytest.mark.integration
class TestAuthLoginEndpoint:
    @pytest.mark.asyncio
    async def test_login_valid_credentials_returns_tokens(self, async_client: AsyncClient):
        # Register first
        await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "logintest@example.com",
                "password": "Strong@123",
                "first_name": "Login",
                "last_name": "Test",
            },
        )

        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "logintest@example.com", "password": "Strong@123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password_returns_401(self, async_client: AsyncClient):
        await async_client.post(
            "/api/v1/auth/register",
            json={
                "email": "wrongpass@example.com",
                "password": "Correct@123",
                "first_name": "A",
                "last_name": "B",
            },
        )
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "wrongpass@example.com", "password": "Wrong@123"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_unknown_email_returns_401(self, async_client: AsyncClient):
        response = await async_client.post(
            "/api/v1/auth/login",
            json={"email": "nobody@example.com", "password": "Any@1234"},
        )
        assert response.status_code == 401


@pytest.mark.integration
class TestProtectedEndpoint:
    @pytest.mark.asyncio
    async def test_get_profile_without_token_returns_403(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/users/me")
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_get_profile_with_valid_token_returns_200(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        response = await async_client.get("/api/v1/users/me", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "email" in data
        assert "id" in data
