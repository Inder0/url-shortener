import pytest
from httpx import AsyncClient
from .helpers import create_test_user,auth_header,login_user
from unittest.mock import AsyncMock,patch

@pytest.mark.anyio
async def test_create_user(client: AsyncClient):
    response = await client.post(
        "/api/v1/users",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "Testpassword123@",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"


@pytest.mark.anyio
async def test_create_user_duplicate_username(client:AsyncClient):
    await create_test_user(client)
    response=await client.post(
        "/api/v1/users",
        json={"username":"testuser","email":"test1@example.com","password":"Password123@"}
    )
    assert response.status_code==400
    assert response.json()["detail"]=="Username already exists"


@pytest.mark.anyio
async def test_create_user_duplicate_email(client:AsyncClient):
    await create_test_user(client)
    response=await client.post(
        "/api/v1/users",
        json={"username":"testuser1","email":"test@example.com","password":"Password123@"}
    )
    assert response.status_code==400
    assert response.json()["detail"]=="Email already exists"


@pytest.mark.anyio
async def test_create_user_success(client:AsyncClient):
    response=await client.post(
        "/api/v1/users",
        json={"username":"testuser1","email":"test1@example.com","password":"Password123@"}
    )
    assert response.status_code==201
    data=response.json()
    assert data["username"]=="testuser1"
    assert data["email"]=="test1@example.com"
    assert "id" in data
    assert "image_path" in data
    assert "password" not in data
    assert "password_hash" not in data

@pytest.mark.anyio
async def test_login_success(client:AsyncClient):
    await create_test_user(client)

    response=await client.post(
        "/api/v1/users/token",
        data={
            "username":"test@example.com",
            "password":"Testpassword123@"
        }
    )

    assert response.status_code==200

    data=response.json()

    assert "access_token" in data
    assert data["token_type"]=="bearer"


@pytest.mark.anyio
async def test_login_wrong_password(client:AsyncClient):
    await create_test_user(client)

    response=await client.post(
        "/api/v1/users/token",
        data={
            "username":"test@example.com",
            "password":"Wrongpassword123@"
        }
    )

    assert response.status_code==401
    assert response.json()["detail"]=="Incorrect email or password"


@pytest.mark.anyio
async def test_login_user_not_found(client:AsyncClient):
    response=await client.post(
        "/api/v1/users/token",
        data={
            "username":"doesnotexist@example.com",
            "password":"Testpassword123@"
        }
    )

    assert response.status_code==401
    assert response.json()["detail"]=="Incorrect email or password"


@pytest.mark.anyio
async def test_get_current_user(client:AsyncClient):
    await create_test_user(client)
    token=await login_user(client)

    response=await client.get(
        "/api/v1/users/me",
        headers=auth_header(token)
    )

    assert response.status_code==200

    data=response.json()

    assert data["username"]=="testuser"
    assert data["email"]=="test@example.com"
    assert "password" not in data
    assert "password_hash" not in data


@pytest.mark.anyio
async def test_get_current_user_unauthorized(client:AsyncClient):
    response=await client.get("/api/v1/users/me")

    assert response.status_code==401


@pytest.mark.anyio
async def test_get_current_user_invalid_token(client:AsyncClient):
    response=await client.get(
        "/api/v1/users/me",
        headers=auth_header("invalid_token")
    )

    assert response.status_code==401


@pytest.mark.anyio
async def test_update_user(client:AsyncClient):
    await create_test_user(client)
    token=await login_user(client)

    response=await client.patch(
        "/api/v1/users",
        headers=auth_header(token),
        json={
            "username":"updateduser",
            "email":"updated@example.com"
        }
    )

    assert response.status_code==200

    data=response.json()

    assert data["username"]=="updateduser"
    assert data["email"]=="updated@example.com"


@pytest.mark.anyio
async def test_update_user_duplicate_username(client:AsyncClient):
    await create_test_user(client)

    await create_test_user(
        client,
        username="testuser2",
        email="test2@example.com"
    )

    token=await login_user(client)

    response=await client.patch(
        "/api/v1/users",
        headers=auth_header(token),
        json={"username":"testuser2"}
    )

    assert response.status_code==400
    assert response.json()["detail"]=="Username already exists"


@pytest.mark.anyio
async def test_update_user_duplicate_email(client:AsyncClient):
    await create_test_user(client)

    await create_test_user(
        client,
        username="testuser2",
        email="test2@example.com"
    )

    token=await login_user(client)

    response=await client.patch(
        "/api/v1/users",
        headers=auth_header(token),
        json={"email":"test2@example.com"}
    )

    assert response.status_code==400
    assert response.json()["detail"]=="Email already exists"
