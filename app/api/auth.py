import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from app.models.models import UserCreate, UserLogin, UserResponse, Token
from app.database.connection import get_collection
from app.auth.jwt_handler import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate):
    """Register a new user (Student or Admin)."""
    users_collection = get_collection("users")
    
    # Check if user already exists
    existing_user = await users_collection.find_one({"email": user_in.email})
    if existing_user:
        logger.warning(f"Registration failed: Email {user_in.email} already exists.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check if this is the first user in the database. If so, make them an admin by default!
    # This is a very helpful developer tool.
    user_count = await users_collection.count_documents({})
    role = user_in.role
    if user_count == 0:
        role = "admin"
        logger.info(f"First user registered. Overriding role to 'admin' for {user_in.email}.")
        
    hashed_pwd = hash_password(user_in.password)
    
    user_dict = {
        "name": user_in.name,
        "email": user_in.email,
        "password": hashed_pwd,
        "role": role,
        "created_at": datetime.utcnow()
    }
    
    result = await users_collection.insert_one(user_dict)
    user_dict["_id"] = result.inserted_id
    
    logger.info(f"Successfully registered user {user_in.email} with role {role}.")
    return user_dict

@router.post("/login", response_model=Token)
async def login(credentials: UserLogin):
    """Authenticate credentials and generate access token."""
    users_collection = get_collection("users")
    user = await users_collection.find_one({"email": credentials.email})
    
    if not user or not verify_password(credentials.password, user["password"]):
        logger.warning(f"Failed login attempt for email {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generate token
    token_data = {"sub": user["email"], "role": user["role"]}
    access_token = create_access_token(data=token_data)
    
    logger.info(f"User {credentials.email} logged in successfully.")
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "role": user["role"],
        "name": user["name"]
    }

@router.get("/me", response_model=UserResponse)
async def me(current_user: dict = Depends(get_current_user)):
    """Retrieve the current logged-in user profile."""
    return current_user
