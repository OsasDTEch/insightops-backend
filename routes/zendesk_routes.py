from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
import os
import httpx
from dotenv import load_dotenv

load_dotenv()

ZENDESK_SESSION_SECRET = os.environ.get("ZENDESK_SESSION_SECRET")
ZENDESK_SUBDOMAIN = os.environ.get("ZENDESK_SUB_DOMAIN")  # e.g., yourcompany.zendesk.com
ZENDESK_CLIENT_ID = os.environ.get("ZENDESK_ID")
ZENDESK_CLIENT_SECRET = os.environ.get("ZENDESK_CLIENT_SECRET")
ZENDESK_REDIRECT_URL = os.environ.get("ZENDESK_REDIRECT_URL")  # e.g., https://yourapp.com/zendesk/callback

router = APIRouter(prefix="/zendesk", tags=["Zendesk"])


# Step 1: Redirect user to Zendesk OAuth page
@router.get("/connect")
def connect_zendesk():
    oauth_url = (
        f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/oauth/authorizations/new"
        f"?response_type=code&client_id={ZENDESK_CLIENT_ID}"
        f"&redirect_uri={ZENDESK_REDIRECT_URL}&scope=read write"
    )
    return RedirectResponse(url=oauth_url)


# Step 2: Callback URL to handle Zendesk's response
@router.get("/callback")
async def zendesk_callback(request: Request, code: str = None, error: str = None):
    if error:
        raise HTTPException(status_code=400, detail=f"Zendesk OAuth error: {error}")

    if not code:
        raise HTTPException(status_code=400, detail="No authorization code provided by Zendesk")

    # Exchange code for access token
    token_url = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/oauth/tokens"
    payload = {
        "grant_type": "authorization_code",
        "client_id": ZENDESK_CLIENT_ID,
        "client_secret": ZENDESK_CLIENT_SECRET,
        "redirect_uri": ZENDESK_REDIRECT_URL,
        "code": code,
    }

    async with httpx.AsyncClient() as client:
        resp = await client.post(token_url, data=payload)

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    token_data = resp.json()
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")

    # TODO: Save tokens securely in your DB, linked to the user's workspace
    return {"access_token": access_token, "refresh_token": refresh_token, "token_data": token_data}


# Optional: Test fetching Zendesk tickets
@router.get("/tickets")
async def get_tickets(access_token: str):
    url = f"https://{ZENDESK_SUBDOMAIN}.zendesk.com/api/v2/tickets.json"
    headers = {"Authorization": f"Bearer {access_token}"}

    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=headers)

    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail=resp.text)

    return resp.json()
