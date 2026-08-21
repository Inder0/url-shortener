# URL Shortener API

An API-first URL shortening service built with **FastAPI**, **PostgreSQL**, **Redis**, and **async SQLAlchemy**.

## Live Demo

https://linkly-shortener.onrender.com

> **Note:** The live API is deployed on Render's free tier. After a period of inactivity, the service may spin down and the first request can take about a minute while it starts back up.

> **Password reset:** The password-reset flow is fully implemented and works out of the box in local/Docker deployments. The live Render free-tier deployment cannot send SMTP traffic because Render blocks outbound SMTP ports `25`, `465`, and `587` on free web services. Email delivery therefore does not work on the live demo without using an external email API or a paid Render instance. citeturn776759search0turn776759search1


The service provides authenticated URL management, custom aliases, expiration, click tracking, analytics, Redis-backed redirect caching, rate limiting, pagination, and Dockerized development/testing.

## Features

* JWT-based authentication
* Secure password hashing
* User registration and profile management
* URL creation, retrieval, update, and deletion
* Automatically generated short codes
* Optional custom aliases
* URL expiration
* Redis caching for redirect lookups
* Click tracking
* Click analytics
* Paginated URL and click endpoints
* Search URLs by title
* Per-endpoint rate limiting
* Ownership-based authorization
* Async PostgreSQL access with SQLAlchemy
* Database migrations with Alembic
* Dockerized application, PostgreSQL, and Redis
* Dedicated PostgreSQL test database
* Automated async API tests with pytest
* Interactive OpenAPI documentation through Swagger UI

---

## Tech Stack

| Component        | Technology              |
| ---------------- | ----------------------- |
| API              | FastAPI                 |
| Language         | Python                  |
| Database         | PostgreSQL              |
| ORM              | SQLAlchemy 2.0 (async)  |
| Cache            | Redis                   |
| Authentication   | JWT + OAuth2 Bearer     |
| Password hashing | `pwdlib`                |
| Validation       | Pydantic v2             |
| Rate limiting    | SlowAPI                 |
| Migrations       | Alembic                 |
| Testing          | Pytest + HTTPX          |
| Containerization | Docker + Docker Compose |
| Server           | Uvicorn                 |

---

## Architecture

```text
                           ┌───────────────────┐
                           │      Client       │
                           │  Swagger / App    │
                           └─────────┬─────────┘
                                     │
                                     ▼
                           ┌───────────────────┐
                           │      FastAPI      │
                           │      API v1       │
                           └─────────┬─────────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
                    ▼                ▼                ▼
             ┌─────────────┐  ┌─────────────┐  ┌──────────────┐
             │ PostgreSQL  │  │    Redis    │  │ Rate Limiter │
             │   Source    │  │   Cache     │  │    Redis     │
             │   of Truth  │  │  Redirects  │  │              │
             └─────────────┘  └─────────────┘  └──────────────┘
```

### PostgreSQL

PostgreSQL is the primary source of truth for:

* users
* URLs
* click records

Async SQLAlchemy is used for database access.

### Redis

Redis is used for the highest-frequency read path: URL redirection.

A redirect request first checks Redis using the short code:

```text
GET /abc123
      │
      ▼
Redis lookup: url:abc123
      │
      ├── Cache hit ────────► Redirect
      │
      └── Cache miss
                │
                ▼
          PostgreSQL lookup
                │
                ▼
          Store in Redis
                │
                ▼
             Redirect
```

Click records are still persisted in PostgreSQL.

Redis is also used as the storage backend for API rate limiting.

---

## API Versioning

API endpoints are versioned under:

```text
/api/v1
```

The redirect endpoint intentionally remains outside the API namespace because it represents the public short-link itself.

Example:

```text
POST /api/v1/urls
GET  /api/v1/urls
GET  /api/v1/urls/{url_id}
```

Public redirect:

```text
GET /{short_code}
```

---

# Authentication

Authentication uses JWT access tokens with OAuth2 Bearer authentication.

When a user logs in, the API creates a token containing:

```json
{
  "sub": "user_id",
  "exp": "expiration"
}
```

Protected endpoints extract the user ID from the token and load the corresponding user from PostgreSQL.

Passwords are never stored directly. They are hashed using `pwdlib`.

## Authentication flow

```text
Register
   │
   ▼
Password hashed
   │
   ▼
PostgreSQL
```

```text
Login
   │
   ▼
Verify password
   │
   ▼
Create JWT
   │
   ▼
Bearer token
```

Protected requests then use:

```http
Authorization: Bearer <access_token>
```

---

# URL Shortening

URLs can be created with either:

1. an automatically generated short code
2. a custom alias

### Generated short code

When no alias is supplied, the URL's database ID is encoded using Base62 to generate a compact short code.

Example:

```text
Database ID: 12345
      ↓
Base62 encoding
      ↓
Short code: dnh
```

### Custom alias

A caller can optionally provide an alias:

```json
{
  "url": "https://github.com/Inder0",
  "title": "GitHub",
  "alias": "github"
}
```

The resulting public URL becomes:

```text
https://your-domain.com/github
```

Aliases are validated and must be unique.

If the alias is omitted, normal automatic short-code generation is used.

---

# URL Expiration

URLs can be created with a configurable expiration period.

Example:

```json
{
  "url": "https://example.com",
  "title": "Example",
  "expires_in_days": 30
}
```

Expiration is tracked relative to the URL's expiration update timestamp.

When an expired URL is requested, the API returns:

```http
410 Gone
```

rather than redirecting the request.

Updating the expiration period also refreshes the expiration timestamp.

---

# Click Tracking

Every successful redirect records a click in PostgreSQL.

The click record includes:

* timestamp
* source IP address
* user agent
* referrer
* associated URL

Example:

```text
URL
 │
 └── Click
      ├── clicked_at
      ├── ip_address
      ├── user_agent
      └── referer
```

This provides the underlying data required for analytics without coupling analytics to the redirect cache.

---

# Analytics

Each authenticated URL owner can retrieve analytics for their URLs.

The analytics endpoint provides:

* total clicks
* clicks today
* clicks in the last 7 days
* clicks in the last 30 days
* timestamp of the most recent click

Example:

```http
GET /api/v1/urls/{url_id}/analytics
```

Response:

```json
{
  "total_clicks": 481,
  "clicks_today": 17,
  "clicks_last_7_days": 93,
  "clicks_last_30_days": 314,
  "last_clicked": "2026-08-20T13:42:11Z"
}
```

A separate endpoint exposes paginated click records.

---

# Pagination and Search

URL listing supports pagination:

```http
GET /api/v1/urls?page=1&page_size=15
```

and title search:

```http
GET /api/v1/urls?q=github
```

Responses include pagination metadata:

```json
{
  "total": 42,
  "page_int": 1,
  "page_size": 15,
  "total_pages": 3,
  "results": []
}
```

Click history is also paginated.

---

# Authorization

Authenticated users can only manage their own URLs.

For example:

```text
GET    /api/v1/urls/{id}
PATCH  /api/v1/urls/{id}
DELETE /api/v1/urls/{id}
GET    /api/v1/urls/{id}/analytics
GET    /api/v1/urls/{id}/clicks
```

all verify that the requested URL belongs to the authenticated user.

This prevents users from reading or modifying another user's links.

---

# Rate Limiting

Rate limiting is implemented using **SlowAPI** with Redis as the backing store.

Different operations have different limits based on their expected usage.

Examples include:

```text
User registration
URL creation
URL updates
URL deletion
Authentication
```

This protects endpoints that are more susceptible to abuse while allowing normal read operations to remain lightweight.

---

# API Endpoints

## Users

### Register

```http
POST /api/v1/users
```

Create a new user account.

### Login

```http
POST /api/v1/users/token
```

Returns a JWT access token.

### Current User

```http
GET /api/v1/users/me
```

Returns the authenticated user's information.

### Public User

```http
GET /api/v1/users/{user_id}
```

Returns public user information.

### Update User

```http
PATCH /api/v1/users
```

Updates the authenticated user's profile information.

### Delete User

```http
DELETE /api/v1/users
```

Deletes the authenticated user.

---

## URLs

### Create URL

```http
POST /api/v1/urls
```

Create a shortened URL.

Example request:

```json
{
  "url": "https://example.com/very/long/path",
  "title": "Example",
  "expires_in_days": 30,
  "alias": "example"
}
```

### List URLs

```http
GET /api/v1/urls
```

Supports pagination and title search.

### Get URL

```http
GET /api/v1/urls/{url_id}
```

### Update URL

```http
PATCH /api/v1/urls/{url_id}
```

### Delete URL

```http
DELETE /api/v1/urls/{url_id}
```

### Analytics

```http
GET /api/v1/urls/{url_id}/analytics
```

### Click History

```http
GET /api/v1/urls/{url_id}/clicks
```

---

## Redirect

Public redirect endpoint:

```http
GET /{short_code}
```

Example:

```text
GET /github
```

The service resolves the short code and redirects the client to the destination URL.

A successful redirect returns:

```http
307 Temporary Redirect
```

An expired URL returns:

```http
410 Gone
```

A missing URL returns:

```http
404 Not Found
```

---

# API Documentation

FastAPI automatically generates interactive documentation.

After starting the application:

### Swagger UI

```text
http://localhost:8000/docs
```

### OpenAPI schema

```text
http://localhost:8000/openapi.json
```

Swagger can be used to test authenticated endpoints, create URLs, inspect responses, and explore the API without a separate frontend.

---

# Health Check

The service exposes:

```http
GET /health
```

The endpoint checks database connectivity and returns:

```json
{
  "status": "OK"
}
```

---

# Project Structure

```text
url-shortener/
│
├── alembic/
│   ├── versions/
│   └── env.py
│
├── routers/
│   ├── urls.py
│   └── users.py
│
├── tests/
│   ├── conftest.py
│   ├── helpers.py
│   ├── test_urls.py
│   └── test_users.py
│
├── utils/
│   └── base62.py
│
├── auth.py
├── config.py
├── database.py
├── main.py
├── models.py
├── rate_limiter.py
├── redis_client.py
├── schemas.py
│
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── alembic.ini
└── .gitignore
```

### Responsibilities

`main.py`

* application initialization
* lifespan management
* router registration
* health endpoint
* redirect handling
* global exception handling

`routers/`

* HTTP/API routes
* request handling
* authorization
* database interaction

`models.py`

* SQLAlchemy ORM models
* relationships
* URL expiration logic
* derived URL properties

`schemas.py`

* Pydantic request/response models
* request validation
* API response serialization

`auth.py`

* password hashing
* password verification
* JWT creation
* JWT validation
* current-user dependency

`database.py`

* asynchronous SQLAlchemy engine
* session management
* declarative base

`redis_client.py`

* asynchronous Redis client configuration

`rate_limiter.py`

* SlowAPI configuration
* Redis-backed request limiting

`utils/base62.py`

* short-code generation

`alembic/`

* database migration history

`tests/`

* API integration tests
* authentication tests
* URL management tests
* validation tests

---

# Docker Setup

The project includes a Docker Compose environment containing:

```text
┌────────────────────────┐
│        app             │
│      FastAPI           │
│       :8000            │
└───────────┬────────────┘
            │
      ┌─────┴──────┐
      │            │
      ▼            ▼
┌──────────┐  ┌──────────┐
│ Postgres │  │  Redis   │
│  :5432   │  │  :6379   │
└──────────┘  └──────────┘
```

## Start the application

```bash
docker compose up --build
```

The API will be available at:

```text
http://localhost:8000
```

Swagger:

```text
http://localhost:8000/docs
```

---

# Environment Variables

Create a `.env` file locally.

Example:

```env
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/url_shortener
SYNC_DATABASE_URL=postgresql://postgres:postgres@db:5432/url_shortener

DOMAIN_NAME=http://localhost:8000

EXPIRES_IN_DAYS=30

REDIS_URL=redis://redis:6379/
```

Do not commit the real `.env` file.

A `.env.example` file should be used for documenting the required configuration without exposing secrets.

---

# Database Migrations

Alembic is used for schema migrations.

Apply all migrations:

```bash
docker compose exec app alembic upgrade head
```

Create a new migration:

```bash
docker compose exec app alembic revision --autogenerate -m "describe change"
```

Rollback the latest migration:

```bash
docker compose exec app alembic downgrade -1
```

The application database and test database are kept separate.

---

# Testing

The project uses:

* `pytest`
* `pytest-asyncio`/AnyIO support
* HTTPX
* a dedicated PostgreSQL test database

The tests run inside the Docker application container.

Run the full test suite:

```bash
docker compose exec app pytest -v
```

The current suite contains **21 tests** covering authentication, users, URL creation, validation, searching, authorization, aliases, and duplicate handling.

Example:

```text
21 passed
```

## Test database

Docker creates a separate database:

```text
url_shortener_test
```

The normal application database remains:

```text
url_shortener
```

This prevents tests from modifying development data.

The test database is disposable; the test fixtures create and remove the required schema during the test lifecycle.

---

# Local Development Without Docker

Docker is the recommended way to run the complete stack because the application depends on both PostgreSQL and Redis.

For direct local execution, make sure PostgreSQL and Redis are running and configure the environment variables accordingly.

Install dependencies:

```bash
pip install -r requirements.txt
```

Apply migrations:

```bash
alembic upgrade head
```

Run the API:

```bash
uvicorn main:app --reload
```

Run tests:

```bash
pytest -v
```

---

# Request Flow

## Creating a URL

```text
Client
  │
  ▼
POST /api/v1/urls
  │
  ▼
JWT authentication
  │
  ▼
Validate request
  │
  ▼
Create URL record
  │
  ▼
Generate Base62 short code
(or use custom alias)
  │
  ▼
PostgreSQL
  │
  ▼
Return API representation
```

## Redirecting

```text
Client
  │
  ▼
GET /abc123
  │
  ▼
Redis lookup
  │
  ├─────────────── cache hit ───────────────┐
  │                                         │
  ▼                                         ▼
PostgreSQL lookup                      Destination URL
  │                                         │
  ▼                                         │
Validate expiration                         │
  │                                         │
  ▼                                         │
Cache destination                           │
  │                                         │
  └─────────────────────────────────────────┘
                    │
                    ▼
             Record click
                    │
                    ▼
           307 Temporary Redirect
```

---

# Design Decisions

## Why PostgreSQL?

URL ownership, metadata, expiration information, and click records are relational data with clear relationships.

PostgreSQL provides the consistency and querying capabilities needed for:

* ownership checks
* pagination
* click aggregation
* analytics
* unique short codes
* transactional updates

## Why Redis?

Redirects are expected to be much more frequent than administrative URL operations.

Caching the short-code-to-destination mapping allows the hottest read path to avoid a PostgreSQL query when the value is already cached.

## Why asynchronous SQLAlchemy?

The application uses FastAPI's asynchronous request handling, so asynchronous database access allows database I/O to integrate naturally with the async request lifecycle.

## Why JWT?

The API is designed to be consumed independently of a frontend. Stateless Bearer authentication makes the API easy to use from web applications, mobile applications, scripts, and other clients.

## Why Base62?

Base62 produces compact identifiers using:

```text
0-9
a-z
A-Z
```

It provides shorter human-friendly codes than exposing sequential numeric IDs directly.

## Why store click information separately?

Redis is used to accelerate link resolution, while PostgreSQL remains the durable source of truth for analytics.

Separating these concerns means cache behavior does not determine whether click history is persisted.

---

# Error Handling

The API uses standard HTTP status codes for common conditions.

Examples:

```text
201 Created
200 OK
204 No Content
400 Bad Request
401 Unauthorized
404 Not Found
409 Conflict
410 Gone
422 Unprocessable Entity
429 Too Many Requests
```

Examples include:

* invalid request data → `422`
* invalid credentials → `401`
* missing/unauthorized resource → `404` or `401`
* duplicate alias → `409`
* expired URL → `410`
* rate limit exceeded → `429`

---

# Security Considerations

* Passwords are hashed before storage.
* Password hashes are never returned through public user schemas.
* JWTs are signed and validated before protected operations.
* Token expiration is enforced.
* Protected URL operations verify resource ownership.
* Rate limiting protects sensitive endpoints.
* Request validation is handled through Pydantic.
* Secrets are supplied through environment variables rather than committed to source control.

---

# Future Improvements

The project is intentionally kept focused around its API-first use case.

Potential future improvements could include:

* background click processing
* richer analytics aggregation
* API keys for service-to-service clients
* refresh tokens
* OpenTelemetry instrumentation
* CI-based automated tests
* production deployment configuration
* metrics and monitoring

These are intentionally outside the current core implementation.

---

# Running the Project

The shortest Docker workflow is:

```bash
docker compose up --build
```

Apply database migrations:

```bash
docker compose exec app alembic upgrade head
```

Run tests:

```bash
docker compose exec app pytest -v
```

Open Swagger:

```text
http://localhost:8000/docs
```

Health check:

```text
http://localhost:8000/health
```

---

# Summary

This project focuses on building a small but complete backend service rather than a frontend-heavy URL shortening application.

The main engineering goals are:

* async API development with FastAPI
* relational data modeling with PostgreSQL
* Redis-backed caching
* JWT authentication
* resource ownership
* URL expiration
* analytics and click tracking
* rate limiting
* database migrations
* automated integration tests
* reproducible Docker-based development

The API is designed to be consumed independently by any client capable of making HTTP requests.
