"""
Integration tests for health check endpoints.
"""
import pytest
from httpx import AsyncClient


@pytest.mark.integration
class TestHealthEndpoints:
    @pytest.mark.asyncio
    async def test_health_returns_200(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "uptime_seconds" in data

    @pytest.mark.asyncio
    async def test_live_returns_200(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/live")
        assert response.status_code == 200
        assert response.json()["status"] == "alive"
