# intercom_routes.py
import os
import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from database.db import get_db
from models import Integration
from auth.validate_users import get_current_user, get_user_workspace

load_dotenv()

INTERCOM_CLIENT_ID = os.getenv("INTERCOM_CLIENT_ID")
INTERCOM_CLIENT_SECRET = os.getenv("INTERCOM_CLIENT_SECRET")
INTERCOM_REDIRECT_URI = os.getenv("INTERCOM_REDIRECT_URI")

router = APIRouter(prefix="/intercom", tags=["Intercom"])

# ---------------------------
# Step 1: Redirect user to Intercom OAuth page
# ---------------------------
@router.get("/authorize")
async def intercom_authorize():
    redirect_url = (
        f"https://app.intercom.com/oauth?client_id={INTERCOM_CLIENT_ID}"
        f"&redirect_uri={INTERCOM_REDIRECT_URI}"
        f"&state=some_random_string"
        f"&scope=read,write"
    )
    return {"auth_url": redirect_url}

# ---------------------------
# Step 2: Handle OAuth callback
# ---------------------------
@router.get("/callback")
async def intercom_callback(
    code: str = None,
    state: str = None,
    workspace_id: str = None,  # optional query param for multi-workspace users
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    if not code:
        raise HTTPException(status_code=400, detail="No code returned from Intercom")

    # Get workspace for current user
    workspace = get_user_workspace(current_user, workspace_id)

    # Exchange code for access token
    token_url = "https://api.intercom.io/auth/eagle/token"
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            token_url,
            json={
                "grant_type": "authorization_code",
                "client_id": INTERCOM_CLIENT_ID,
                "client_secret": INTERCOM_CLIENT_SECRET,
                "redirect_uri": INTERCOM_REDIRECT_URI,
                "code": code
            },
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
        )
        token_data = resp.json()

    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail=f"Failed to fetch access token: {token_data}")

    # Save or update Integration record
    integration = db.query(Integration).filter_by(
        workspace_id=workspace.id,
        type="intercom"
    ).first()

    if not integration:
        integration = Integration(
            workspace_id=workspace.id,
            type="intercom",
            name="Intercom",
            config={"access_token": access_token}
        )
        db.add(integration)
    else:
        integration.config["access_token"] = access_token

    db.commit()
    db.refresh(integration)

    return {"message": "Intercom token saved successfully", "integration_id": integration.id}
