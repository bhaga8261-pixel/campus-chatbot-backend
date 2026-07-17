import logging
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.config.settings import settings
from app.database.connection import get_collection
from app.models.models import TokenData
from bson import ObjectId

logger = logging.getLogger(__name__)

# Password hashing configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
ALGORITHM = "HS256"

# Token URL corresponds to the login endpoint
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against the hashed version."""
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generate a JWT access token containing user metadata."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """
    Dependency to authenticate a user from a JWT token in the Authorization header.
    Returns the user document from the database.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_101_SWITCHING_PROTOCOLS, # Standard Unauthorized setup: 401 Unauthorized
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    # Fix exception status code to 401
    credentials_exception.status_code = status.HTTP_401_UNAUTHORIZED

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email, role=role)
    except JWTError:
        raise credentials_exception

    users_collection = get_collection("users")
    user = await users_collection.find_one({"email": token_data.email})
    if user is None:
        raise credentials_exception
    
    return user

async def get_current_admin(current_user: dict = Depends(get_current_user)) -> dict:
    """
    Dependency to verify that the logged-in user is an administrator.
    """
    if current_user.get("role") != "admin":
        logger.warning(f"Unauthorized access attempt to admin resource by user {current_user.get('email')}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user does not have enough privileges"
        )
    return current_user
