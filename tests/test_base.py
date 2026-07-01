# ** Base Modules
from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock

from fastapi import status

# ** App Modules
from app.core.database import get_db
from app.main import app, client


def _mock_db_override() -> AsyncMock:
    """Return a mock AsyncSession that can execute SELECT 1."""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock(return_value=MagicMock())
    return mock_session


def test_home() -> None:
    """Health check should return 200 when the DB session is available."""

    async def override_get_db() -> AsyncIterator[AsyncMock]:
        yield _mock_db_override()

    app.dependency_overrides[get_db] = override_get_db
    try:
        response = client.get("/api/health")
        assert response.status_code == status.HTTP_200_OK
    finally:
        app.dependency_overrides.pop(get_db, None)


def test_pulse() -> None:
    """Pulse check should always return 200 (no DB dependency)."""
    response = client.get("/api/pulse")
    assert response.status_code == status.HTTP_200_OK
