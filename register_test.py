import json
import sys

import requests

url = "http://127.0.0.1:8001/auth/register"
payload = {
    "name": "Test User",
    "email": "testuser@example.com",
    "password": "Password123!",
    "confirm_password": "Password123!"
}
headers = {"Content-Type": "application/json"}
try:
    resp = requests.post(url, data=json.dumps(payload), headers=headers)
    print("Status:", resp.status_code)
    print("Response:", resp.text)
except Exception as e:
    print("Error:", e)
    sys.exit(1)
