from fastapi import APIRouter,HTTPException,status,Depends,Request,BackgroundTasks
from schemas import UserPrivate,UserCreate,Token,UserPublic,UserUpdate,ResetPasswordRequest,ForgotPasswordRequest
from typing import Annotated
from database import AsyncSession,get_db
from sqlalchemy import select,func
from sqlalchemy import delete as sql_delete
import models
import re
from auth import hash_password,verify_password,create_access_token,CurrentUser,generate_reset_token,hash_reset_token
from fastapi.security import OAuth2PasswordRequestForm
from config import settings
from rate_limiter import limiter
from datetime import datetime,UTC,timedelta
from email_utils import send_reset_email

router=APIRouter()

@router.post("",response_model=UserPrivate,status_code=status.HTTP_201_CREATED)
@limiter.limit("3/minute")
async def create_user(request:Request,user:UserCreate,db:Annotated[AsyncSession,Depends(get_db)]):
    user.username=user.username.strip()
    user.email=user.email.strip()
    result=await db.execute(select(models.User).where(func.lower(models.User.username)==user.username.lower()))
    existing_user=result.scalars().first()
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Username already exists")

    result= await db.execute(select(models.User).where(func.lower(models.User.email)==user.email.lower()))
    existing_user=result.scalars().first()
    if existing_user:
        raise(HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Email already exists"))
    password = user.password

    if (
        not re.search(r"[A-Z]", password)
        or not re.search(r"[a-z]", password)
        or not re.search(r"\d", password)
        or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password)
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, one number and one special character."
            ),
        )
    new_user=models.User(
        username=user.username,
        email=user.email.lower(),
        password_hash=hash_password(password)
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.post("/token",response_model=Token)
@limiter.limit("5/minute")
async def login_for_access_token(request:Request,form_data:Annotated[OAuth2PasswordRequestForm,Depends()],db:Annotated[AsyncSession,Depends(get_db)]):
    result=await db.execute(select(models.User).where(func.lower(models.User.email)==form_data.username.lower()))
    user=result.scalars().first()
    if not user or not verify_password(form_data.password,user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="Incorrect email or password")
    access_token_expires=settings.access_token_expire_minutes
    access_token=create_access_token(
        data={"sub":str(user.id)},
        expires_delta=access_token_expires
    )
    return Token(access_token=access_token,token_type="bearer")

@router.get("/me",response_model=UserPrivate)
async def get_current_user(current_user:CurrentUser):
    return current_user

@router.get("/{user_id}",response_model=UserPublic)
@limiter.limit("20/minute")
async def get_user(request:Request,user_id:int,db:Annotated[AsyncSession,Depends(get_db)]):
    result=await db.execute(select(models.User).where(models.User.id==user_id))
    user=result.scalars().first()
    if user:
        return user
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="User not found")

@router.patch("",response_model=UserPrivate)
@limiter.limit("5/minute")
async def update_user(request:Request,current_user:CurrentUser,db:Annotated[AsyncSession,Depends(get_db)],user_data:UserUpdate):
    user=await db.execute(select(models.User).where(models.User.id==current_user.id))
    user=user.scalars().first()
    if user_data.username is not None and user_data.username.lower()!=user.username.lower():
        result=await db.execute(select(models.User).where(func.lower(models.User.username)==user_data.username.lower()))
        existing_user=result.scalars().first()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Username already exists")
    if user_data.email is not None and user_data.email.lower()!=current_user.email.lower():
        result=await db.execute(select(models.User).where(func.lower(models.User.email)==user_data.email.lower()))
        existing_user=result.scalars().first()
        if existing_user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Email already exists")

    update_user=user_data.model_dump(exclude_unset=True,exclude_none=True)
    for key,value in update_user.items():
        if key == "username" and value is not None:
            value = value.strip()
        elif key == "email" and value is not None:
            value = value.strip().lower()
        setattr(user,key,value)

    await db.commit()
    await db.refresh(user)
    return user

@router.delete("",status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(current_user:CurrentUser,db:Annotated[AsyncSession,Depends(get_db)]):
    await db.delete(current_user)
    await db.commit()


@router.post("/forgot-password",status_code=status.HTTP_202_ACCEPTED)
async def forgot_password(request_data:ForgotPasswordRequest,background_tasks:BackgroundTasks,db:Annotated[AsyncSession,Depends(get_db)]):
    result=await db.execute(select(models.User).where(func.lower(models.User.email)==request_data.email.lower()))
    user=result.scalars().first()
    if user:
        await db.execute(sql_delete(models.PasswordResetToken).where(models.PasswordResetToken.user_id==user.id))
        token=generate_reset_token()
        token_hash=hash_reset_token(token)
        expires_at=datetime.now(UTC)+timedelta(minutes=settings.reset_token_expire_mins)
        reset_token=models.PasswordResetToken(
            user_id=user.id,
            token_hash=token_hash,
            expires_at=expires_at
        )
        db.add(reset_token)
        await db.commit()
        background_tasks.add_task(
            send_reset_email,
            to_email=user.email,
            username=user.username,
            token=token
        )
    return {"message":"If an account exists with this email,you will receive password reset instructions."}

@router.post("/reset-password",status_code=status.HTTP_200_OK)
async def reset_password(request_data:ResetPasswordRequest,db:Annotated[AsyncSession,Depends(get_db)]):
    token_hash=hash_reset_token(request_data.token)
    result=await db.execute(select(models.PasswordResetToken).where(models.PasswordResetToken.token_hash==token_hash))
    reset_token=result.scalars().first()
    if not reset_token:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Invalid or expired reset token")
    if reset_token.expires_at<datetime.now(UTC):
        await db.delete(reset_token)
        await db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Invalid or expired reset token")
    result=await db.execute(select(models.User).where(models.User.id==reset_token.user_id))
    user=result.scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Invalid or expired reset token")
    password = request_data.new_password
    if (
        not re.search(r"[A-Z]", password)
        or not re.search(r"[a-z]", password)
        or not re.search(r"\d", password)
        or not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password)
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, one number and one special character."
            ),
        )
    user.password_hash=hash_password(request_data.new_password)
    await db.execute(sql_delete(models.PasswordResetToken).where(models.PasswordResetToken.user_id==user.id))
    await db.commit()
    return {"message":"Password Reset Successful."}
        
