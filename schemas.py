from pydantic import BaseModel,ConfigDict,Field,EmailStr
from datetime import datetime
from pydantic import AnyHttpUrl
from typing import Optional

class UserBase(BaseModel):
    username:str
    

class UserPublic(UserBase):
    model_config=ConfigDict(from_attributes=True)
    id:int
    image:str | None
    image_path:str |None

class UserPrivate(UserPublic):
    email:EmailStr

class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    email: EmailStr | None = None
    
class UserCreate(BaseModel):
    username:str=Field(min_length=1,max_length=50)
    email:EmailStr=Field()
    password:str=Field(min_length=8)


class Token(BaseModel):
    access_token:str
    token_type:str


class URLCreate(BaseModel):
    url:AnyHttpUrl
    title:str=Field(min_length=1,max_length=100)
    expires_in_days:int| None=Field(default=None,ge=1,le=3650)
    alias:Optional[str]=Field(default=None,min_length=3,max_length=32,pattern=r"^[A-Za-z0-9_-]+$")

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{
                "url": "https://example.com/",
                "title": "Example URL",
                "expires_in_days": 30,
                "alias": "my-link"
            }
        ]})

class URLPublic(BaseModel):
    model_config=ConfigDict(from_attributes=True,ge=1,le=3650)
    id:int
    url:str
    title:str
    expires_in_days:int|None
    short_code:str
    redirect_url:str |None
    created_at:datetime
    expiry_updated_at:datetime

class URLWithClicks(URLPublic):
    click_count:int


class URLUpdate(BaseModel):
    url:AnyHttpUrl|None=Field(default=None,min_length=1)
    title:str|None=Field(default=None,min_length=1,max_length=100)
    expires_in_days:int|None=Field(default=None,ge=1,le=3650)

class URLAnalytics(BaseModel):
    total_clicks: int
    clicks_today: int
    clicks_last_7_days: int
    clicks_last_30_days: int
    last_clicked: datetime | None

class ClickPublic(BaseModel):
    model_config=ConfigDict(from_attributes=True)
    id:int
    clicked_at:datetime
    ip_address:str | None
    user_agent:str | None
    referer:str | None

class PaginatedClicks(BaseModel):
    total:int
    page_int:int
    page_size:int
    total_pages:int
    results:list[ClickPublic]

class PaginatedURLs(BaseModel):
    total:int
    page_int:int
    page_size:int
    total_pages:int
    results:list[URLWithClicks]


