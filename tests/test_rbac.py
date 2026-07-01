from app.main import client


def test_me_without_login() -> None:
    response = client.get("/rbac/me")
    assert response.status_code in [401, 403]


def test_users_without_login() -> None:
    response = client.get("/rbac/users")
    assert response.status_code in [401, 403]


def test_roles_without_login() -> None:
    response = client.get("/rbac/roles")
    assert response.status_code in [401, 403]


def test_permissions_without_login() -> None:
    response = client.get("/rbac/permissions")
    assert response.status_code in [401, 403]


def test_reports_without_login() -> None:
    response = client.get("/rbac/reports")
    assert response.status_code in [401, 403]
