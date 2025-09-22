from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database.db import get_db
from database.models import User, Workspace, Membership
from auth.auth import hash_password, create_access_token, verify_password
from auth.validate_users import get_current_user

from database.schemas import UserCreate, UserOut
from datetime import datetime, timedelta
from database import schemas, models
import os
load_dotenv()
router = APIRouter(prefix="/auth", tags=["Auth"])
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 30))
@router.post("/signup", response_model=UserOut)
def signup(user_in: UserCreate, db: Session = Depends(get_db)):
    # Check if user exists
    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # Create user
    user = User(
        email=user_in.email,
        hashed_password=hash_password(user_in.password),
        full_name=user_in.full_name
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create default workspace
    workspace = Workspace(name=f"{user_in.full_name or user_in.email}'s Workspace")
    db.add(workspace)
    db.commit()
    db.refresh(workspace)

    # Link membership
    membership = Membership(user_id=user.id, workspace_id=workspace.id, role="owner")
    db.add(membership)
    db.commit()

    return UserOut(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        workspace_id= workspace.id,
        role=membership.role,
        created_at=user.created_at,
        status_code=201,
        message="Signup successful"
    )

@router.post("/login", response_model=schemas.LoginResponse)
def login(email: str, password: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )

    user_out = schemas.LoginUserOut(
        id=user.id,
        full_name=user.full_name,
        email=user.email
    )

    return schemas.LoginResponse(
        status_code=200,
        message="Login successful",
        user=user_out,
        access_token=access_token
    )

@router.get("/me", response_model=schemas.UserOutMultiple)
def read_me(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    memberships = db.query(models.Membership).filter(models.Membership.user_id == current_user.id).all()

    membership_list = [
        schemas.UserMembership(
            workspace_id=str(m.workspace_id),
            role=m.role
        )
        for m in memberships
    ]

    return schemas.UserOutMultiple(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        memberships=membership_list,
        created_at=str(current_user.created_at),
        status_code=200,
        message="User fetched successfully"
    )

