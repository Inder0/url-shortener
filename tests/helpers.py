import pytest
from httpx import AsyncClient

async def create_test_user(
        client:AsyncClient,
        username:str="testuser",
        email:str="test@example.com",
        password:str="Testpassword123@"

) -> dict:
    response=await client.post(
        "/api/v1/users",
        json={
            "username":username,
            "email":email,
            "password":password

        })
    assert response.status_code==201,f"Failed to create user: {response.text}"
    return response.json()

async def login_user(
        client:AsyncClient, 
        email:str="test@example.com",
        password:str="Testpassword123@"

) -> str:
    response=await client.post(
        "/api/v1/users/token",
        data={
            "username":email,
            "password":password

        })
    assert response.status_code==200,f"Failed to login user: {response.text}"
    return response.json()["access_token"]

def auth_header(token:str) -> dict[str,str]:
    return {"Authorization":f"Bearer {token}"}