from app.main import client


def test_invalid_blog_update() -> None:
    response = client.put(
        "/blogs/99999",
        json={}
    )

    assert response.status_code in [404, 401, 403, 422]


def test_invalid_blog_update_duplicate() -> None:
    response = client.put(
        "/blogs/99999",
        json={}
    )

    assert response.status_code in [404, 401, 403, 422]


def test_invalid_blog_status() -> None:
    response = client.put(
        "/blogs/1/status",
        json={"status": "XYZ"}
    )

    assert response.status_code in [400, 401, 403, 422]


def test_blog_analytics() -> None:
    response = client.get("/blogs/analytics")

    assert response.status_code in [200, 401, 403]


def test_upload_invalid_file() -> None:
    files = {
        "file": ("test.txt", b"hello world", "text/plain")
    }

    response = client.post(
        "/blogs/upload-image",
        files=files
    )

    assert response.status_code in [400, 401, 403]
