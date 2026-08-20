from database import Base
from sqlalchemy import Integer,String,Text,DateTime,ForeignKey,select,func
from sqlalchemy.orm import mapped_column,Mapped,relationship,column_property
from datetime import datetime,UTC,timedelta
from config import settings

class User(Base):
    __tablename__="users"
    id:Mapped[int]=mapped_column(Integer,primary_key=True,index=True)
    username:Mapped[str]=mapped_column(String(50),unique=True,nullable=False)
    email:Mapped[str]=mapped_column(String(150),unique=True,nullable=False)
    image:Mapped[str|None]=mapped_column(String(200),nullable=True,default=None)
    password_hash:Mapped[str]=mapped_column(String(255),nullable=False)
    urls:Mapped[list[URL]]=relationship(back_populates="user",cascade="all, delete-orphan")

    @property
    def image_path(self):
        if self.image:
            return f"/media/profile_pics/{self.image}"

        return "/static/images/default_avatar.png"

class URL(Base):
    __tablename__="urls"
    id:Mapped[int]=mapped_column(Integer,primary_key=True,index=True)
    url:Mapped[str]=mapped_column(Text,nullable=False)
    title:Mapped[str]=mapped_column(String(100),nullable=False,index=True)
    expires_in_days:Mapped[int]=mapped_column(Integer,nullable=False,default=30)
    user_id:Mapped[int]=mapped_column(ForeignKey("users.id"),nullable=False,index=True)
    short_code:Mapped[str]=mapped_column(String(32),unique=True,nullable=True,index=True)
    created_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda: datetime.now(UTC))
    expiry_updated_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda: datetime.now(UTC))

    user:Mapped[User]=relationship("User",back_populates="urls")
    clicks:Mapped[list["Click"]]=relationship("Click",back_populates="url",cascade="all, delete-orphan",)


    @property
    def redirect_url(self):
        return f"{settings.domain_name}/{self.short_code}"

    @property
    def expired(self):
        if self.expiry_updated_at:
            if datetime.now(UTC)>self.expiry_updated_at+timedelta(days=self.expires_in_days):
                return True
        elif self.created_at:
            if datetime.now(UTC)>self.created_at+timedelta(days=self.expires_in_days):
                return True
        else:
            return False



class Click(Base):
    __tablename__="clicks"
    id:Mapped[int]=mapped_column(Integer,primary_key=True,index=True)
    url_id:Mapped[int]=mapped_column(ForeignKey("urls.id"),nullable=False,index=True)
    clicked_at:Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda: datetime.now(UTC))
    ip_address:Mapped[str|None]=mapped_column(String(50),nullable=True)
    user_agent:Mapped[str|None]=mapped_column(String,nullable=True)
    referer:Mapped[str|None]=mapped_column(String,nullable=True)

    url:Mapped[URL]=relationship("URL",back_populates="clicks")
