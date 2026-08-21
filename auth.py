from pwdlib import PasswordHash
from fastapi.security import OAuth2PasswordBearer
from datetime import timedelta,datetime,UTC
from config import settings
import jwt
from typing import Annotated
from fastapi import Depends,HTTPException,status
from database import AsyncSession,get_db
from sqlalchemy import select
import models
import secrets
import hashlib

password_hash=PasswordHash.recommended()

oauth2_scheme=OAuth2PasswordBearer(tokenUrl="/api/v1/users/token")

def hash_password(password: str) -> str:
    return password_hash.hash(password)

def verify_password(plain_password:str,hashed_password:str) -> bool:
    return password_hash.verify(plain_password,hashed_password)

def generate_reset_token() -> str:
    return secrets.token_urlsafe(32)

def hash_reset_token(token:str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_access_token(data:dict,expires_delta:timedelta | None=None) -> str:
    to_encode=data.copy()
    if expires_delta:
        expire=datetime.now(UTC)+timedelta(minutes=expires_delta)
    else:
        expire=datetime.now(UTC)+timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({"exp":expire})
    encoded_jwt=jwt.encode(
        to_encode,
        settings.secret_key.get_secret_value(),
        algorithm=settings.algorithm
    )
    return encoded_jwt

def verify_access_token(token:str)->str|None:
    try:
        payload=jwt.decode(
            token,
            settings.secret_key.get_secret_value(),
            algorithms=[settings.algorithm],
            options={"require":["exp","sub"]}
        )
    except jwt.InvalidTokenError:
        return None
    else:
        return payload.get("sub")

async def get_current_user(token:Annotated[str,Depends(oauth2_scheme)],db:Annotated[AsyncSession,Depends(get_db)]):
    user_id=verify_access_token(token)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid or Expired token",headers={"WWW-Authenticate":"Bearer"})
    try:
        user_id=int(user_id)
    except (ValueError,TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid or Expired token",headers={"WWW-Authenticate":"Bearer"})
    result=await db.execute(select(models.User).where(models.User.id==user_id))
    user=result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Invalid or Expired token",headers={"WWW-Authenticate":"Bearer"})
    return user

CurrentUser=Annotated[models.User,Depends(get_current_user)]