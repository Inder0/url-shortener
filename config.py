from pydantic_settings import BaseSettings,SettingsConfigDict
from pydantic import SecretStr
from datetime import timedelta

class Settings(BaseSettings):
    model_config=SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8"
    )

    secret_key:SecretStr 
    algorithm:str="HS256"
    access_token_expire_minutes:int=30
    database_url:str | None=None
    sync_database_url:str | None=None
    domain_name:str ="localhost:8000"
    expires_in_days:int=30
    redis_url:str
    env:str
    mail_username: str
    mail_password: SecretStr
    mail_from: str
    reset_token_expire_mins:int=60



settings=Settings()