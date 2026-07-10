# Orbit Backend Starter

![CI](https://github.com/TuranAymis/orbit-backend/actions/workflows/ci.yml/badge.svg)

Orbit is a FastAPI starter backend for a local social community and event platform. It includes authentication, modular domain models, PostgreSQL persistence, Alembic migrations, and ready-to-extend routes for users, groups, memberships, events, chats, and payments.

## Stack

- Python 3.12+
- FastAPI
- PostgreSQL
- SQLAlchemy 2.0 ORM
- Alembic
- Pydantic
- JWT bearer authentication
- Passlib bcrypt password hashing

## Included Features

- Environment-driven settings with `.env`
- JWT auth with register and login flows
- UUID primary keys across the main domain models
- SQLAlchemy relationships and indexes for common lookups
- CRUD and service separation
- Protected `/users/me` endpoint
- Health check endpoint at `/health`
- Seed helper for a bootstrap local user
- Alembic autogenerate-ready configuration
- Local CORS defaults for common frontend dev ports

## Project Structure

```bash
orbit-backend/
  app/
    api/
    core/
    crud/
    models/
    schemas/
    services/
    utils/
    main.py
    seed.py
  alembic/
  alembic.ini
  requirements.txt
  .env.example
  README.md
```

## Local Setup

### 1. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Create the PostgreSQL database

Make sure PostgreSQL is running locally, then create the database:

```bash
psql -U postgres -h localhost -p 5432 -c "CREATE DATABASE orbit_db;"
```

If your local PostgreSQL setup already has `orbit_db`, you can skip this step.

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and replace `JWT_SECRET_KEY` with a secure value before production use.

### 5. Create and apply the first migration

Generate the initial migration:

```bash
alembic revision --autogenerate -m "create initial tables"
```

Apply the migration:

```bash
alembic upgrade head
```

### 6. Seed a bootstrap local user

Create a default local account:

```bash
python -m app.seed
```

Override the defaults if needed:

```bash
python -m app.seed --email owner@example.com --password StrongPass123! --full-name "Orbit Owner"
```

### 7. Run the API server

```bash
uvicorn app.main:app --reload
```

The API will start at:

- `http://127.0.0.1:8000`

### 8. Open the docs

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

## Example Auth Flow

### Register

```bash
curl -X POST "http://127.0.0.1:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "full_name": "Jane Doe",
    "email": "jane@example.com",
    "password": "StrongPass123!",
    "membership_level": "free"
  }'
```

### Login

```bash
curl -X POST "http://127.0.0.1:8000/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "jane@example.com",
    "password": "StrongPass123!"
  }'
```

Sample response:

```json
{
  "access_token": "your.jwt.token",
  "token_type": "bearer",
  "expires_in": 3600
}
```

### Call a protected route

```bash
curl "http://127.0.0.1:8000/users/me" \
  -H "Authorization: Bearer your.jwt.token"
```

## Notes

- Group creation also creates an owner membership record automatically.
- `GET /chats` returns the current user's own messages when no `group_id` or `event_id` filter is supplied.
- Payments are scoped to the authenticated user in the starter implementation.
- Events can be managed by group owners or active group admins.

## Development Tips

- Health check: `GET /health`
- To create new migrations after model changes:

```bash
alembic revision --autogenerate -m "describe your change"
alembic upgrade head
```

- If you need a clean reset during development, drop and recreate the database, then rerun migrations.

```bash
python -m app.seed --email owner@example.com --password StrongPass123! --full-name "Orbit Owner"
```
