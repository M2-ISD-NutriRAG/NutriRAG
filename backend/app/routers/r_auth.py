from fastapi import APIRouter, HTTPException, Response
from app.models.m_auth import LoginRequest, LoginResponse, StartAuthRequest

import snowflake.connector
import os

router = APIRouter()

@router.post("/login")
def login(payload: StartAuthRequest):
    print(f"Attempting login for account: {payload.account}")
    try:
        # This will OPEN Snowflake's login page in the browser
        conn = snowflake.connector.connect(
            account=payload.account,
            user=os.getenv("SNOWFLAKE_USER"),
            authenticator="EXTERNALBROWSER",
        )

        conn.close()

        # If we reach here → auth succeeded
        return {"ok": True}

    except Exception as e:
        print(e)
        raise HTTPException(status_code=401, detail="Authentication failed")
