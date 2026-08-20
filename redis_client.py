from redis.asyncio import Redis
from config import settings

redis=Redis.from_url(
    f"{settings.redis_url}/0",
    decode_responses=True
)