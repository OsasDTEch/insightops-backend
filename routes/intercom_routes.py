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
async def intercom_callback(request: Request):
    # Intercom will redirect here with ?code=...&state=...
    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if not code:
        return {"error": "Missing code in callback"}

    # Exchange code for access token
    token_url = "https://api.intercom.io/oauth/token"
    payload = {
        "grant_type": "authorization_code",
        "client_id": INTERCOM_CLIENT_ID,
        "client_secret": INTERCOM_CLIENT_SECRET,
        "redirect_uri": INTERCOM_REDIRECT_URI,
        "code": code
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(token_url, json=payload)
        data = response.json()

    # data now contains 'access_token' for this workspace
    return {"oauth_response": data}
