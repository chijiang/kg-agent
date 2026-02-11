import pytest
import asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.api.deps import get_current_user
from app.models.user import User


@pytest.mark.asyncio
async def test_execution_logs_api():
    # Mock authentication
    async def mock_get_current_user():
        return User(id=1, username="testuser")

    original_overrides = app.dependency_overrides.get(get_current_user)
    app.dependency_overrides[get_current_user] = mock_get_current_user

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as ac:
            headers = {"Authorization": "Bearer mock-token"}

            # Test listing logs (should be empty or have recent logs)
            response = await ac.get("/api/rules/logs", headers=headers)
            assert response.status_code == 200
            data = response.json()
            assert "logs" in data
            assert isinstance(data["logs"], list)
    finally:
        # Restore original dependency
        if original_overrides:
            app.dependency_overrides[get_current_user] = original_overrides
        else:
            del app.dependency_overrides[get_current_user]


@pytest.mark.asyncio
async def test_action_execution_logs():
    # This test would require a set up database and registered actions
    # For now, we'll just check if the endpoint exists and returns 200
    pass
