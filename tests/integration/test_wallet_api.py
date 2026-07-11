"""
Integration tests for Wallet API endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestWalletEndpoints:
    @pytest.mark.asyncio
    async def test_create_wallet_returns_201(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        response = await async_client.post(
            "/api/v1/wallets",
            json={"currency": "USD", "label": "My Main Wallet"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["currency"] == "USD"
        assert data["balance"] == "0"
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_create_duplicate_currency_wallet_returns_409(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        await async_client.post(
            "/api/v1/wallets",
            json={"currency": "EUR"},
            headers=auth_headers,
        )
        response = await async_client.post(
            "/api/v1/wallets",
            json={"currency": "EUR"},
            headers=auth_headers,
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_list_wallets_returns_200(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        response = await async_client.get("/api/v1/wallets", headers=auth_headers)
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    @pytest.mark.asyncio
    async def test_wallet_requires_auth(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/wallets")
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_credit_wallet(self, async_client: AsyncClient, auth_headers: dict):
        # Create wallet first
        create_resp = await async_client.post(
            "/api/v1/wallets",
            json={"currency": "GBP"},
            headers=auth_headers,
        )
        wallet_id = create_resp.json()["id"]

        # Credit it
        response = await async_client.post(
            f"/api/v1/wallets/{wallet_id}/credit",
            json={"amount": "500.00", "description": "Initial deposit"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert float(response.json()["balance"]) == 500.0

    @pytest.mark.asyncio
    async def test_debit_exceeding_balance_returns_422(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        create_resp = await async_client.post(
            "/api/v1/wallets",
            json={"currency": "JPY"},
            headers=auth_headers,
        )
        wallet_id = create_resp.json()["id"]

        response = await async_client.post(
            f"/api/v1/wallets/{wallet_id}/debit",
            json={"amount": "999.00"},
            headers=auth_headers,
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "INSUFFICIENT_FUNDS"

    @pytest.mark.asyncio
    async def test_transaction_history_is_paginated(
        self, async_client: AsyncClient, auth_headers: dict
    ):
        create_resp = await async_client.post(
            "/api/v1/wallets",
            json={"currency": "CAD"},
            headers=auth_headers,
        )
        wallet_id = create_resp.json()["id"]

        response = await async_client.get(
            f"/api/v1/wallets/{wallet_id}/transactions?page=1&page_size=10",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "pages" in data
        assert "page" in data
