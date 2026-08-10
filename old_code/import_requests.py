import requests
import csv

auth_url = "https://integrate.elluciancloud.com/auth"

auth_headers = {
    "authorization": "Bearer ETHOSKEY",
    "accept": "application/json",
    "content-type": "text/plain"
}

auth_response = requests.post(
    auth_url,
    headers=auth_headers,
    params={"expirationMinutes": "120"}
)

rec = auth_response.text

api_url = "https://integrate.elluciancloud.com/api/x-xusedpidms"

api_headers = {
    "authorization": f"Bearer {rec}",
    "content-type": "application/json"
}

with open("test.csv", newline="") as f:
    reader = csv.DictReader(f)

    for row in reader:

        payload = {
            "id": "000000",
            "pidmholding": row["spriden_pidm"]
        }
        print(payload)

        response = requests.post(api_url, json=payload, headers=api_headers)

        print(f"{row['spriden_pidm']} -> {response.status_code}")






#1fa12f2a-037d-442d-9f9c-7b27d7f00108