import uuid

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_login_profile_flow(client: AsyncClient) -> None:
    email = f"test_{uuid.uuid4().hex[:8]}@test.com"

    register_response = await client.post(
        "/auth/register",
        json={
            "name": "Integration User",
            "email": email,
            "password": "Password123!",
            "confirm_password": "Password123!",
        },
    )

    assert register_response.status_code in [200, 201]

    login_response = await client.post(
        "/auth/login",
        json={
            "email": email,
            "password": "Password123!",
        },
    )

    assert login_response.status_code == 200

    token = login_response.json()["access_token"]

    profile_response = await client.get(
        "/auth/profile",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert profile_response.status_code == 200
    assert profile_response.json()["email"] == email


@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient) -> None:
    response = await client.post(
        "/auth/login",
        json={
            "email": "wrong@test.com",
            "password": "wrongpass",
        },
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_profile_without_token(client: AsyncClient) -> None:
    response = await client.get("/auth/profile")

    assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_logout_without_token(client: AsyncClient) -> None:
    response = await client.post("/auth/logout")

    assert response.status_code in [401, 403]
