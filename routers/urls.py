from fastapi import APIRouter,status,HTTPException,Depends,Query,Request
from typing import Annotated
from database import AsyncSession,get_db
from sqlalchemy import select,func,desc
from sqlalchemy.orm import selectinload
from auth import CurrentUser
import models
from schemas import URLPublic,URLCreate,URLUpdate,URLAnalytics,PaginatedClicks,PaginatedURLs,URLWithClicks
from datetime import datetime,UTC,timedelta
from utils import base62
from config import settings
import math
from redis_client import redis
from rate_limiter import limiter

router=APIRouter()


@router.post("",response_model=URLPublic,status_code=status.HTTP_201_CREATED)
@limiter.limit("20/minute")
async def create_url(request:Request,data:URLCreate,current_user:CurrentUser,db:Annotated[AsyncSession,Depends(get_db)]):
    new_url=models.URL(
        url=str(data.url),
        title=data.title.strip(),
        user=current_user,
        expires_in_days=data.expires_in_days if data.expires_in_days else settings.expires_in_days
    )
    db.add(new_url)
    await db.flush()
    if data.alias:
        result = await db.execute(select(models.URL).where(models.URL.short_code == data.alias))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,detail="Alias is already in use.")

    new_url.short_code = data.alias or base62.encode(new_url.id)
    await db.commit()
    await db.refresh(new_url)
    result=await db.execute(select(models.URL).options(selectinload(models.URL.clicks)).where(models.URL.id==new_url.id))
    return result.scalar_one()

@router.get("",response_model=PaginatedURLs)
async def get_urls(current_user:CurrentUser,db:Annotated[AsyncSession,Depends(get_db)],q:str|None=None,page:int=Query(1,ge=1),page_size:int=Query(15,ge=1,le=100)):
    offset=(page-1)*page_size
    if q:
        total=await db.execute(select(func.count(models.URL.id)).where(models.URL.user_id==current_user.id,models.URL.title.ilike(f"%{q}%")))
        total=total.scalar_one()
        result=await db.execute(select(models.URL,func.count(models.Click.id).label("click_count")).outerjoin(models.Click).where(models.URL.user_id==current_user.id,models.URL.title.ilike(f"%{q}%")).group_by(models.URL.id).order_by(models.URL.created_at.desc()).offset(offset).limit(page_size))
        rows=result.all()
        
    else:
        total=await db.execute(select(func.count(models.URL.id)).where(models.URL.user_id==current_user.id))
        total=total.scalar_one()
        result=await db.execute(select(models.URL,func.count(models.Click.id).label("click_count")).outerjoin(models.Click).where(models.URL.user_id==current_user.id).group_by(models.URL.id).order_by(models.URL.created_at.desc()).offset(offset).limit(page_size))
        rows=result.all()
    results = []

    for url, click_count in rows:
        data = URLPublic.model_validate(url).model_dump()
        data["click_count"] = click_count
        results.append(URLWithClicks(**data))
    return PaginatedURLs(
        total=total,
        page_int=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size),
        results=results
    )

@router.get("/{url_id}",response_model=URLPublic)
async def get_url(url_id:int,current_user:CurrentUser,db:Annotated[AsyncSession,Depends(get_db)]):
    result=await db.execute(select(models.URL).options(selectinload(models.URL.clicks)).where(models.URL.id==url_id,models.URL.user_id==current_user.id))
    url=result.scalars().first()
    if not url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="URL not found.")
    return url

@router.delete("/{url_id}",status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("10/minute")
async def delete_url(request:Request,url_id:int,current_user:CurrentUser,db:Annotated[AsyncSession,Depends(get_db)]):
    result=await db.execute(select(models.URL).where(models.URL.id==url_id,models.URL.user_id==current_user.id))
    url=result.scalars().first()
    if not url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="URL not found.")
    await db.delete(url)

    await db.commit()
    await redis.delete(f"url:{url.short_code}")

@router.patch("/{url_id}",response_model=URLPublic)
@limiter.limit("20/minute")
async def update_url(request:Request,data:URLUpdate,url_id:int,db:Annotated[AsyncSession,Depends(get_db)],current_user:CurrentUser):
    result=await db.execute(select(models.URL).options(selectinload(models.URL.clicks)).where(models.URL.id==url_id,models.URL.user_id==current_user.id))
    url=result.scalars().first()
    if not url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="URL not found.")
    new_data=data.model_dump(exclude_unset=True)
    if not new_data:
        return url
    for key,value in new_data.items():
        if key=="title":
            value=value.strip()
            if not value:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,detail="Title cannot be empty.")
        elif key=="url":
            value=str(value)
        elif key=="expires_in_days" and value is not None:
            url.expiry_updated_at=datetime.now(UTC)
        setattr(url,key,value)
    await db.commit()
    await redis.delete(f"url:{url.short_code}")
    await db.refresh(url)
    return url


@router.get("/{url_id}/analytics",response_model=URLAnalytics)
async def url_analytics(current_user:CurrentUser,url_id:int,db:Annotated[AsyncSession,Depends(get_db)]):
    result=await db.execute(select(models.URL).where(models.URL.id==url_id,models.URL.user_id==current_user.id))
    url=result.scalars().first()
    if not url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="URL not found.")
    total_clicks=await db.execute(select(func.count(models.Click.id)).where(models.Click.url_id==url_id))
    total_clicks=total_clicks.scalars().first()
    today = datetime.now(UTC).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
        )
    clicks_today=await db.execute(select(func.count(models.Click.id)).where(models.Click.url_id==url_id,models.Click.clicked_at>=today))
    clicks_today=clicks_today.scalars().first()
    week=datetime.now(UTC)-timedelta(days=7)
    clicks_last_7_days=await db.execute(select(func.count(models.Click.id)).where(models.Click.url_id==url_id,models.Click.clicked_at>=week))
    clicks_last_7_days=clicks_last_7_days.scalars().first()
    month=datetime.now(UTC)-timedelta(days=30)
    clicks_last_30_days=await db.execute(select(func.count(models.Click.id)).where(models.Click.url_id==url_id,models.Click.clicked_at>=month))
    clicks_last_30_days=clicks_last_30_days.scalars().first()
    last_click=await db.execute(select(models.Click.clicked_at).where(models.Click.url_id==url_id).order_by(desc(models.Click.clicked_at)).limit(1))
    last_click=last_click.scalars().first()

    return URLAnalytics(
        total_clicks=total_clicks,
        clicks_today=clicks_today,
        clicks_last_30_days=clicks_last_30_days,
        clicks_last_7_days=clicks_last_7_days,
        last_clicked=last_click
    )

@router.get("/{url_id}/clicks",response_model=PaginatedClicks)
async def get_clicks(current_user:CurrentUser,url_id:int,db:Annotated[AsyncSession,Depends(get_db)],page:int=Query(1,ge=1),page_size:int=Query(20,ge=1,le=100)):
    result=await db.execute(select(models.URL).where(models.URL.id==url_id,models.URL.user_id==current_user.id))
    url=result.scalars().first()
    if not url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="URL not found.")

    total=await db.execute(select(func.count(models.Click.id)).where(models.Click.url_id==url_id))
    total=total.scalar_one()
    offset=(page-1)*page_size
    result=await db.execute(
        select(models.Click)
        .where(models.Click.url_id==url_id)
        .order_by(models.Click.clicked_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    clicks=result.scalars().all()
    return PaginatedClicks(
        total=total,
        page_int=page,
        page_size=page_size,
        total_pages=math.ceil(total / page_size),
        results=clicks,
    )