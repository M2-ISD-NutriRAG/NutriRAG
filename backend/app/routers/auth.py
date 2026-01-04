from fastapi import APIRouter, HTTPException, Response
from app.models.auth import LoginRequest, LoginResponse, StartAuthRequest

from urllib.parse import urlencode
import snowflake.connector
import os

import requests
import base64

router = APIRouter()

@router.get("/me")
def me():
    return None


@router.post("/login/snowflake")
def login(payload: StartAuthRequest):
    # 1. Your app credentials (from your Snowflake SECURITY INTEGRATION)
    CLIENT_ID = os.getenv("CLIENT_ID") 
    REDIRECT_URI = os.getenv("REDIRECT_URI")
    
    # 2. Clean up the account name 
    # (Ensure any dots from 'org.account' are replaced with hyphens for the URL)
    account_identifier = payload.account.replace(".", "-")
    
    try:
        # 3. Define the query parameters
        params = {
            "client_id": CLIENT_ID,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            # "state": "optional_random_security_string" 
        }

        # 4. Construct the full Snowflake Auth URL
        base_url = f"https://{account_identifier}.snowflakecomputing.com/oauth/authorize"
        snowflake_auth_url = f"{base_url}?{urlencode(params)}"

        print(f"Redirecting user to: {snowflake_auth_url}")

        return {
            "ok": True, 
            "redirectUrl": snowflake_auth_url
        }
    


    except Exception as e:
        print(f"Error constructing URL: {e}")
        raise HTTPException(status_code=500, detail="Could not generate Auth URL")
    
@router.post("/login/finalize")
def finalize_snowflake_login(payload: dict):
    code = payload.get("code")
    # Get the account name sent from the frontend
    account = payload.get("account") 
    
    if not account:
        raise HTTPException(status_code=400, detail="Account identifier is required")

    # Format it for the URL (replace dots with hyphens)
    account_id = account.replace(".", "-")
    
    CLIENT_ID = os.getenv("CLIENT_ID")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")
    REDIRECT_URI = os.getenv("REDIRECT_URI")
    
    # DYNAMIC URL
    token_url = f"https://{account_id}.snowflakecomputing.com/oauth/token-request"

    basic_auth_str = f"{CLIENT_ID}:{CLIENT_SECRET}"
    encoded_auth = base64.b64encode(basic_auth_str.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {encoded_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }

    response = requests.post(token_url, headers=headers, data=data)

    if response.status_code != 200:
        print(f"Error from Snowflake token endpoint: {response.text}")
        raise HTTPException(status_code=500, detail="Failed to exchange code for token")
    
    token_response = response.json()
    access_token = token_response.get("access_token")
    refresh_token = token_response.get("refresh_token")
    expires_in = token_response.get("expires_in")

    return {
        "ok": True,
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_in": expires_in
    }