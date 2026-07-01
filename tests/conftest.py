import os
from collections.abc import AsyncIterator

import pytest_asyncio
from dotenv import load_dotenv
from httpx import ASGITransport, AsyncClient

from app.main import app

env_file = ".env.test" if os.getenv("ENV_MODE") == "test" else ".env"
load_dotenv(env_file)


@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
