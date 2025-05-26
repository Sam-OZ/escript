import requests
import os
import jwt
import datetime
import uuid
import urllib.parse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

def generate_jwt(private_key_path: str) -> str:
    """
    Generate a JWT using RS256 algorithm and a provided RSA private key.
    The payload matches the expected structure required by the token exchange API.
    """
    with open(private_key_path, "rb") as key_file:
        private_key = key_file.read()

    now = datetime.datetime.now(datetime.timezone.utc)
    exp = now + datetime.timedelta(hours=1)  # Token expires in 1 hour

    payload = {
        "sub": "mysl\\internal\\My Processor",
        "name": "My Processor",
        "iss": "Televita|1.0",
        "aud": "https://fhir.medicationknowledge.com.au",
        "exp": int(exp.timestamp()),
        "iat": int(now.timestamp()),
        "nbf": int(now.timestamp()),
        "jti": str(uuid.uuid4()),
        "pesType": "eRx"
    }

    return jwt.encode(payload, private_key, algorithm="RS256")

import time

def get_access_token(retries: int = 3, delay: int = 5):
    """
    Request an access token from the Medication Knowledge API
    with retry logic in case of temporary server issues.
    """
    url = "https://auth-int.medicationknowledge.com.au/connect/token"
    subject_token = generate_jwt("converted_private_key.pem")

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Ocp-Apim-Subscription-Key": os.getenv("OCP_APIM_SUBSCRIPTION_KEY"),
        "User-Agent": "PostmanRuntime/7.32.2"
    }

    data = {
        "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
        "client_id": os.getenv("CLIENT_ID"),
        "client_secret": os.getenv("CLIENT_SECRET"),
        "scope": os.getenv("SCOPE"),
        "subject_token": subject_token,
        "subject_token_type": "urn:ietf:params:oauth:token-type:jwt"
    }

    data_encoded = urllib.parse.urlencode(data)

    for attempt in range(1, retries + 1):
        try:
            response = requests.post(url, headers=headers, data=data_encoded, verify=True)
            if response.status_code == 200:
                return response.json().get("access_token")
            elif response.status_code == 520:
                print(f"⚠️  520 Web server error on attempt {attempt}. Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                raise Exception(f"Token request failed: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"⚠️  Request error: {e}. Retrying in {delay} seconds...")
            time.sleep(delay)

    raise Exception("❌ Failed to obtain token after multiple attempts.")


if __name__ == "__main__":
    try:
        token = get_access_token()
        print("✅ Access Token:", token)
    except Exception as e:
        print("❌ Error:", e)
