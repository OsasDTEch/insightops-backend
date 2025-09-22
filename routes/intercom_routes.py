import os
import httpx
from fastapi import APIRouter, Request
from dotenv import load_dotenv

load_dotenv()

INTERCOM_CLIENT_ID = os.getenv("INTERCOM_CLIENT_ID")
INTERCOM_CLIENT_SECRET = os.getenv("INTERCOM_CLIENT_SECRET")
INTERCOM_REDIRECT_URI = os.getenv("INTERCOM_REDIRECT_URI")

router = APIRouter(prefix="/intercom", tags=["Intercom"])

# Step 1: Redirect user to Intercom OAuth page
@router.get("/authorize")
async def intercom_authorize():
    redirect_url = (
        f"https://app.intercom.com/oauth?client_id={INTERCOM_CLIENT_ID}"
        f"&redirect_uri={INTERCOM_REDIRECT_URI}"
        f"&state=some_random_string"
        f"&scope=read,write"
    )
    return {"auth_url": redirect_url}


# Step 2: Handle OAuth callback
@router.get("/callback")
async def intercom_callback(code: str = None, state: str = None):
    if not code:
        return {"error": "No code returned from Intercom"}

    token_url = "https://api.intercom.io/auth/eagle/token"

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            token_url,
            json={  # <- use json= instead of data=
                "grant_type": "authorization_code",
                "client_id": INTERCOM_CLIENT_ID,
                "client_secret": INTERCOM_CLIENT_SECRET,
                "redirect_uri": INTERCOM_REDIRECT_URI,
                "code": code
            },
            headers={
                "Accept": "application/json",  # required
                "Content-Type": "application/json"
            }
        )
        token_data = resp.json()

    # Save token_data['access_token'] to DB here
    return {"token_data": token_data}

