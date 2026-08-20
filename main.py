from fastapi import FastAPI,Request,status
from datetime import datetime,UTC,timedelta
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text,select
from fastapi import Depends
from database import engine,get_db,AsyncSession
from typing import Annotated
from starlette.exceptions import HTTPException as StarHTTPException
from fastapi.exception_handlers import http_exception_handler,request_validation_exception_handler
from fastapi.exceptions import RequestValidationError,HTTPException
from fastapi.staticfiles import StaticFiles
from routers import users,urls
import models
from redis_client import redis
import json
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from rate_limiter import limiter

@asynccontextmanager
async def lifespan(_app:FastAPI):
    await redis.ping()
    yield
    await redis.aclose()
    await engine.dispose()

app=FastAPI(lifespan=lifespan)
templates=Jinja2Templates(directory="templates")

app.state.limiter=limiter
app.add_exception_handler(RateLimitExceeded,_rate_limit_exceeded_handler)

app.mount("/static",StaticFiles(directory="static"),name="static")

app.include_router(users.router,prefix="/api/v1/users",tags=["users"])
app.include_router(urls.router,prefix="/api/v1/urls",tags=["urls"])

@app.get("/health",include_in_schema=False)
async def health(db: Annotated[AsyncSession,Depends(get_db)]):
    await db.execute(text("SELECT 1"))
    return {"status": "OK"}

@app.get("/",include_in_schema=False)
def home(request:Request):
    return templates.TemplateResponse(request,"home.html")

@app.get("/{short_code}",include_in_schema=False)
async def redirect_url(request:Request,short_code:str,db:Annotated[AsyncSession,Depends(get_db)]):
    cached=await redis.get(f"url:{short_code}")
    if cached:
        data=json.loads(cached)
        click=models.Click(
            url_id=data["id"],
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
            referer=request.headers.get("referer"),
        )
        db.add(click)
        await db.commit()
        return RedirectResponse(data["url"],status_code=status.HTTP_307_TEMPORARY_REDIRECT)
    result=await db.execute(select(models.URL).where(models.URL.short_code==short_code))
    url=result.scalars().first()
    if not url:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="URL not found.")
    if url.expired:
        raise HTTPException(status_code=status.HTTP_410_GONE,detail="This URL has expired.")
    await redis.set(
        f"url:{short_code}",
        json.dumps({"id":url.id,"url":url.url}),
        ex=int((url.expiry_updated_at+timedelta(days=url.expires_in_days)-datetime.now(UTC)).total_seconds())
    )
    click=models.Click(
        url_id=url.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        referer=request.headers.get("referer"),
    )
    db.add(click)
    await db.commit()
    return RedirectResponse(url.url,status_code=status.HTTP_307_TEMPORARY_REDIRECT)

@app.exception_handler(StarHTTPException)
async def general_http_exception_handler(request:Request,exception:StarHTTPException):
    return await http_exception_handler(request,exception)

@app.exception_handler(RequestValidationError)
async def general_http_exception_handler(request:Request,exception:RequestValidationError):
    return await request_validation_exception_handler(request,exception)