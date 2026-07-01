import sys

import requests

access_token = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiI5IiwiZW1haWwiOiJ0ZXN0dXNlckBleGFtcGxlLmNvbSIsImV4cCI6MTc4MDkxMDc3OCwidHlwZSI6ImFjY2VzcyJ9."
    "JvsDg9IF1vNgwlLiNm8ckdnb4OZ-d4mGUlXKx63y5F8"
)
url = "http://127.0.0.1:8001/auth/profile"
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}
try:
    resp = requests.get(url, headers=headers)
    print("Status:", resp.status_code)
    print("Response:", resp.text)
except Exception as e:
    print("Error:", e)
    sys.exit(1)
