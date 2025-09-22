from dotenv import load_dotenv
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
import os

from database.db import get_db
from database import models
from sqlalchemy.orm import Session

load_dotenv()

SECRET_KEY = os.getenv("AUTH_SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(models.User).filter(
        models.User.id == user_id).first()  # Remove int() conversion since user_id is now a string
    if user is None:
        raise credentials_exception
    return user


def get_user_workspace(user: models.User, workspace_id: str = None):
    """
    If workspace_id is passed, return that membership;
    Otherwise, return the first workspace (or the owner's workspace).
    """
    memberships = user.memberships  # list of Membership objects
    if not memberships:
        raise HTTPException(status_code=400, detail="User has no workspace")

    if workspace_id:
        for m in memberships:
            if str(m.workspace_id) == workspace_id:
                return m.workspace
        raise HTTPException(status_code=404, detail="Workspace not found")

    # default to the first workspace
    return memberships[0].workspace
