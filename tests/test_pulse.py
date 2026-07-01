# tests/test_pulse.py

from fastapi import status

from app.main import client


def test_pulse() -> None:
    response = client.get("/api/pulse")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": "I'm Alive"}
