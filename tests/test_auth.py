from app.main import client


def test_profile_without_login() -> None:
    response = client.get("/auth/profile")

    assert response.status_code in [401, 403]


def test_logout_without_login() -> None:
    response = client.post("/auth/logout")

    assert response.status_code in [401, 403]


def test_refresh_token_without_token() -> None:
    response = client.post("/auth/refresh-token")

    assert response.status_code in [400, 401, 403, 422]


def test_login_missing_fields() -> None:
    response = client.post(
        "/auth/login",
        json={}
    )

    assert response.status_code in [400, 401, 422]


def test_register_missing_fields() -> None:
    response = client.post(
        "/auth/register",
        json={}
    )

    assert response.status_code in [400, 422]
