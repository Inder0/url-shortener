from sqlalchemy.ext.asyncio import async_sessionmaker,AsyncSession,create_async_engine
from sqlalchemy.orm import DeclarativeBase
from config import settings

if settings.env=="PRODUCTION":
    connect_args={"ssl":"require"}
else:
    connect_args={}



engine=create_async_engine(
    settings.database_url,
    connect_args=connect_args
)
AsyncSessionLocal=async_sessionmaker(engine,class_=AsyncSession,expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session