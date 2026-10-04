from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

import auth
import models
import schemas
from database import get_db
from dependencies import get_current_user

router = APIRouter(tags=["Auth"])


@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
def register_user(user_data: schemas.UserCreate, db: Session = Depends(get_db)):
    """Registers a new society member with $10,000 starting cash."""
    existing_username = db.query(models.User).filter(models.User.username == user_data.username).first()
    if existing_username:
        raise HTTPException(status_code=400, detail="Username already taken.")

    existing_email = db.query(models.User).filter(models.User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already registered.")

    new_user = models.User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=auth.hash_password(user_data.password)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=schemas.Token)
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Logs in a member and issues a JWT Bearer token."""
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = auth.create_access_token(data={"sub": user.id})
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserResponse)
def get_user_profile(current_user: models.User = Depends(get_current_user)):
    """Protected route: Returns profile info for the currently authenticated member."""
    return current_user