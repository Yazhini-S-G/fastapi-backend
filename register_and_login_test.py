import json
import sys
import uuid

import requests

TEST_PASSWORD = "Password123!"


# Generate a unique email
def generate_email() -> str:
    unique = uuid.uuid4().hex[:8]
    return f"test_{unique}@example.com"


email = generate_email()
register_url = "http://127.0.0.1:8001/auth/register"
login_url = "http://127.0.0.1:8001/auth/login"

payload = {
    "name": "Test User",
    "email": email,
    "password": TEST_PASSWORD,
    "confirm_password": TEST_PASSWORD
}
headers = {"Content-Type": "application/json"}

# Register user
try:
    resp = requests.post(register_url, data=json.dumps(payload), headers=headers)
    print("Register status:", resp.status_code)
    print("Register response:", resp.text)
    if resp.status_code != 200:
        sys.exit(1)
except Exception as e:
    print("Register error:", e)
    sys.exit(1)

# Login user
login_payload = {"email": email, "password": TEST_PASSWORD}
try:
    resp = requests.post(login_url, data=json.dumps(login_payload), headers=headers)
    print("Login status:", resp.status_code)
    print("Login response:", resp.text)
    if resp.status_code != 200:
        sys.exit(1)
    data = resp.json()
    access_token = data.get("access_token")
    print("Access token obtained.")
except Exception as e:
    print("Login error:", e)
    sys.exit(1)
