import json
import sys
import uuid

import requests

unique_id = uuid.uuid4().hex[:8]
email = f"testuser_{unique_id}@example.com"
name = "Test User"
password = "Password123!"

# Register
reg_url = "http://127.0.0.1:8001/auth/register"
reg_payload = {
    "name": name,
    "email": email,
    "password": password,
    "confirm_password": password
}
reg_headers = {"Content-Type": "application/json"}
reg_resp = requests.post(reg_url, data=json.dumps(reg_payload), headers=reg_headers)
print("Register status:", reg_resp.status_code)
print("Register response:", reg_resp.text)
if reg_resp.status_code != 200:
    sys.exit(1)

# Login
login_url = "http://127.0.0.1:8001/auth/login"
login_payload = {"email": email, "password": password}
login_headers = {"Content-Type": "application/json"}
login_resp = requests.post(login_url, data=json.dumps(login_payload), headers=login_headers)
print("Login status:", login_resp.status_code)
print("Login response:", login_resp.text)
if login_resp.status_code != 200:
    sys.exit(1)

login_data = login_resp.json()
access_token = login_data.get("access_token")
print("Access token:", access_token)
