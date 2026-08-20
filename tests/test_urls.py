import pytest
from httpx import AsyncClient
from .helpers import create_test_user,auth_header,login_user


@pytest.mark.anyio
async def test_create_url_success(client:AsyncClient):
    await create_test_user(client)
    token=await login_user(client)

    response=await client.post(
        "/api/v1/urls",
        headers=auth_header(token),
        json={
            "url":"https://example.com",
            "title":"Example"
        }
    )

    assert response.status_code==201

    data=response.json()

    assert data["url"]=="https://example.com/"
    assert data["title"]=="Example"
    assert "id" in data
    assert "short_code" in data

@pytest.mark.anyio
async def test_create_url_invalid_url(client:AsyncClient):
    await create_test_user(client)
    token=await login_user(client)

    response=await client.post(
        "/api/v1/urls",
        headers=auth_header(token),
        json={
            "url":"not-a-url",
            "title":"Example"
        }
    )

    assert response.status_code==422

@pytest.mark.anyio
async def test_create_url_unauthorized(client:AsyncClient):
    response=await client.post(
        "/api/v1/urls",
        json={
            "url":"https://example.com",
            "title":"Example"
        }
    )

    assert response.status_code==401

@pytest.mark.anyio
async def test_get_urls(client:AsyncClient):
    await create_test_user(client)
    token=await login_user(client)

    await client.post(
        "/api/v1/urls",
        headers=auth_header(token),
        json={
            "url":"https://example.com",
            "title":"Example"
        }
    )

    response=await client.get(
        "/api/v1/urls",
        headers=auth_header(token)
    )

    assert response.status_code==200

    data=response.json()

    assert data["total"]==1
    assert len(data["results"])==1
    assert data["results"][0]["title"]=="Example"
    assert data["results"][0]["click_count"]==0

@pytest.mark.anyio
async def test_search_urls(client:AsyncClient):
    await create_test_user(client)
    token=await login_user(client)

    await client.post(
        "/api/v1/urls",
        headers=auth_header(token),
        json={
            "url":"https://example.com",
            "title":"Example Website"
        }
    )

    await client.post(
        "/api/v1/urls",
        headers=auth_header(token),
        json={
            "url":"https://google.com",
            "title":"Google"
        }
    )

    response=await client.get(
        "/api/v1/urls?q=example",
        headers=auth_header(token)
    )

    assert response.status_code==200

    data=response.json()

    assert data["total"]==1
    assert len(data["results"])==1
    assert data["results"][0]["title"]=="Example Website"

@pytest.mark.anyio
async def test_create_url_with_alias(client: AsyncClient):
    await create_test_user(client)
    token = await login_user(client)

    response = await client.post(
        "/api/v1/urls",
        headers=auth_header(token),
        json={
            "url": "https://example.com",
            "title": "Example",
            "alias": "example"
        }
    )

    assert response.status_code == 201

    data = response.json()

    assert data["short_code"] == "example"
    assert data["redirect_url"].endswith("/example")

@pytest.mark.anyio
async def test_create_url_duplicate_alias(client: AsyncClient):
    await create_test_user(client)
    token = await login_user(client)

    payload = {
        "url": "https://example.com",
        "title": "Example",
        "alias": "example"
    }

    first = await client.post(
        "/api/v1/urls",
        headers=auth_header(token),
        json=payload
    )

    second = await client.post(
        "/api/v1/urls",
        headers=auth_header(token),
        json={
            **payload,
            "url": "https://google.com",
            "title": "Google"
        }
    )

    assert first.status_code == 201
    assert second.status_code == 409

@pytest.mark.anyio
async def test_create_url_invalid_alias(client: AsyncClient):
    await create_test_user(client)
    token = await login_user(client)

    response = await client.post(
        "/api/v1/urls",
        headers=auth_header(token),
        json={
            "url": "https://example.com",
            "title": "Example",
            "alias": "bad alias!"
        }
    )

    assert response.status_code == 422