# Spaces Backend API

A concise, developer-focused documentation for the Spaces backend service. This document covers architecture, setup, configuration, data models, and the public API surface so other engineers can understand, run, and extend the project.

## Project Overview

- **Name:** Spaces Backend API
- **Purpose:** Backend for a short-stay/property booking service. Provides user registration & auth, property and room management, bookings, payments, and reviews.
- **Stack:** FastAPI, SQLAlchemy (async), PostgreSQL (asyncpg), Pydantic (v2-style models), Cloudinary (optional for image uploads).

## Quick Start

Prerequisites:
- Python 3.11+
- PostgreSQL reachable by the app
- Optional: Cloudinary account for image uploads

Install and run locally:

```powershell
cd C:\Users\Administrator\Documents\spaces-bk\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Required environment variables
$env:DATABASE_URL = "postgresql+asyncpg://user:pass@localhost:5432/spaces"
$env:SECRET_KEY = "<a-strong-32+-character-secret>"

# Optional: keep app settings in a .env file instead of exporting manually
uvicorn app.main:app --reload
```

The app will be available at `http://127.0.0.1:8000/` and the interactive docs at `/docs`.

If you prefer a `.env` file, the app reads environment variables from the local environment automatically. The most important ones are `DATABASE_URL`, `SECRET_KEY`, and optional `ALLOWED_HOSTS` / `RATE_LIMIT_*` settings.

## Configuration

Configuration is centralized in [app/config.py](app/config.py#L1). Important environment variables:

- `SECRET_KEY` (required): must be at least 32 characters.
- `DATABASE_URL` (recommended): should use the `postgresql+asyncpg://` dialect (the code will convert some legacy schemes).
- `POSTGRES_*`: alternative DB pieces when `DATABASE_URL` is not set.
- `CLOUDINARY_*`: optional credentials for Cloudinary uploads.
- `CORS_ORIGINS`: list of allowed CORS origins.
- `ALLOWED_HOSTS`: explicit, production-safe host allowlist; wildcards are rejected.
- `RATE_LIMIT_ENABLED`, `RATE_LIMIT_MAX_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS`: request throttling settings.
- `ENV`: `development`, `production`, or `test`. Controls docs and error behavior.
- `PAYMENT_WEBHOOK_SECRET`: optional secret for payment webhooks.

See the `Settings` model in [app/config.py](app/config.py#L1) for all available keys and defaults.

## Architecture and Modules

- `app/main.py` — application factory, middleware, static files mount, and router registration. [app/main.py](app/main.py#L1)
- `app/config.py` — environment configuration via Pydantic/Settings. [app/config.py](app/config.py#L1)
- `app/database.py` — SQLAlchemy async engine, session factory, and `Base`. [app/database.py](app/database.py#L1)
- `app/core/` — utilities and cross-cutting concerns:
  - `security.py` — password hashing and JWT creation/validation.
  - `dependencies.py` — FastAPI dependencies (current user, role checks).
  - `exceptions.py` — centralized exception handlers.
  - `logging.py` — logging setup and file rotation.
- `app/models/` — SQLAlchemy models (tables): `User`, `Property`, `Room`, `Booking`, `Payment`, `Review`.
- `app/schemas/` — Pydantic models (request/response shapes).
- `app/crud/` — data-access/business logic layer that performs queries and commit cycles.
- `app/routers/` — API endpoints grouped by feature: `auth`, `users`, `properties`, `rooms`, `bookings`, `payments`, `reviews`.

This project follows a typical layered pattern: routers -> schemas -> crud -> models -> database.

## Database Models (summary)

Source: [app/models/](app/models)

- `User` ([app/models/user.py](app/models/user.py#L1))
  - Fields: `id`, `email`, `hashed_password`, `full_name`, `phone_number`, `role`, `is_active`
  - Helpers: `is_host`, `is_admin`, custom `UserRole` and DB `UserRoleType` mapping.

- `Property` ([app/models/property.py](app/models/property.py#L1))
  - Fields: `id`, `owner_id`, `hotel_name`, `address`, `contact`, `description`, `property_type`, `city`, `state`, `country`, `amenities` (JSON), `images` (JSON), `is_verified`, `avg_rating`, `total_reviews`, timestamps, `is_active`.

- `Room` ([app/models/room.py](app/models/room.py#L1))
  - Fields: `id`, `property_id`, `title`, `description`, `price_per_night`, `images` (JSON).

- `Booking` ([app/models/booking.py](app/models/booking.py#L1))
  - Fields: `id`, `room_id`, `user_id`, `status` (enum), `check_in`, `check_out`, `total_price`, timestamps.

- `Payment` ([app/models/payment.py](app/models/payment.py#L1))
  - Fields: `id`, `booking_id`, `amount`, `currency`, `payment_method`, `status`, `transaction_ref`, `gateway_response`, timestamps.

- `Review` ([app/models/review.py](app/models/review.py#L1))
  - Fields: `id`, `booking_id`, `guest_id`, `property_id`, `rating`, `comment`, `host_response`, timestamps.

Refer to the model files for full field types and constraints.

## Authentication

- JWT-based token auth is used. See [app/core/security.py](app/core/security.py#L1) for token creation and verification.
- Tokens: `access` (short-lived) and `refresh` (longer-lived). `sub` claim stores the user id.
- Dependencies in [app/core/dependencies.py](app/core/dependencies.py#L1) supply `get_current_user`, optional current user, and role-check helpers `require_admin` and `require_host`.
- Access tokens are strictly validated against the `token_type` claim so a refresh token cannot be replayed as an access token.

Authentication endpoints: [app/routers/auth.py](app/routers/auth.py#L1)

## Supported property types

The backend accepts only these property categories when creating or updating a property:

- `hotel`
- `resort`
- `apartment/shortlet`
- `event_spaces`
- `villa`

The API also accepts common user-facing variations such as `Apartment / Shortlet`, `Event Spaces`, and `Villa` through normalization. Values outside this list are rejected with validation errors.

## Security hardening review

I audited the backend against the common API security patterns and fixed the concrete gaps that were present in this codebase.

### Fixed issues

- Token replay protection: refresh/reset tokens are rejected when used as access tokens.
- Password reset safety: reset tokens are no longer echoed in the API response body and are kept server-side instead.
- Host authorization: property creation is now restricted to authenticated hosts/admins via `require_host`.
- Host-header protection: production now uses an explicit `ALLOWED_HOSTS` allowlist instead of wildcard host matching.
- Rate limiting: the app now enforces a lightweight in-memory per-client throttle before requests reach the service layer.

### Review outcome

- No direct BOLA issue was found in the booking/payment ownership checks: these handlers compare the authenticated user id with the resource owner before authorizing access.
- The primary exploitable gaps were in token handling and route-level enforcement, which have been closed.

### Security configuration notes

- Keep `SECRET_KEY` in a secure environment variable or `.env` file; the app rejects weak defaults.
- Set `ALLOWED_HOSTS` to the exact public hostnames for each deployment.
- Keep rate limits low on auth and write endpoints and tune them for production traffic.

## API Reference (high-level)

All endpoints are prefixed with `/api/v1` per router where applicable.

- Auth (`/api/v1/auth`) — registration, login, refresh, logout.
  - POST `/register` — `UserCreate` -> `UserRead` (201)
  - POST `/login` — `UserLogin` -> `Token`
  - POST `/refresh` — accepts `refresh_token` or uses current user, returns new `Token`

- Users (`/api/v1/users`)
  - GET `/me` — returns the currently authenticated user (`UserRead`).
  - PUT `/me` — update current user (`UserUpdate`)
  - GET `/{user_id}` — admin-only, return a user by id.
  - GET `/` — admin-only, list users.

- Properties (`/api/v1/properties`)
  - GET `/` — search properties (filters: `city`, `property_type`, `min_price`, `max_price`, `page`, `limit`).
  - GET `/mine` — list properties for authenticated host.
  - GET `/{property_id}` — property details.
  - POST `/` — create property (multipart form + images) — authenticated host/admin. Accepted `property_type` values: `hotel`, `resort`, `apartment/shortlet`, `event_spaces`, `villa`.
  - PUT `/{property_id}` — update property — owner-only.
  - DELETE `/{property_id}` — deactivate property — owner or admin.
  - PATCH `/{property_id}/verify` — admin-only — set `is_verified`.

- Rooms (`/api/v1/rooms`)
  - GET `/` — list rooms for host (optional `property_id`).
  - POST `/` or `/json` — create room via JSON body (`RoomCreate`).
  - POST `/upload` — create room with uploaded images (form + files).

- Bookings (`/api/v1/bookings`)
  - POST `/` — create booking (`BookingCreate`).
  - GET `/mine` — bookings for current guest.
  - GET `/host-bookings` — bookings for properties owned by host.
  - GET `/{booking_id}` — get booking (owner or admin).
  - DELETE `/{booking_id}` — cancel booking (owner or admin).

- Payments (`/api/v1/payments`)
  - POST `/initiate` — create a payment record for a booking.
  - GET `/mine` — list payments for current guest.
  - GET `/{payment_id}` — get payment detail.
  - POST `/webhook` — payment provider webhook (validates `X-Webhook-Secret`).

- Reviews (`/api/v1/reviews`)
  - POST `/` — create review for a completed booking.
  - GET `/property/{property_id}` — list reviews for a property.
  - PUT `/{review_id}` — update a review (guest only).
  - POST `/{review_id}/host-response` — host can add a response.
  - DELETE `/{review_id}` — admin-only delete.

For request/response shapes, consult the Pydantic schemas in [app/schemas/](app/schemas).

## Uploads & Static Files

- Local uploads are stored under `static/uploads/properties` and served at `/static` via `StaticFiles` mount in [app/main.py](app/main.py#L1).
- The code prefers Cloudinary uploads (see `app/core/cloudinary.py`) but gracefully falls back to local storage.

## Error handling & Logging

- Centralized exception handling is implemented in [app/core/exceptions.py](app/core/exceptions.py#L1). In `development` the handlers return error details; in `production` they return generic messages.
- Logging configured in [app/core/logging.py](app/core/logging.py#L1) with rotating files in `logs/app.log`.

## Testing

- There's a basic tests folder present. Add tests using `pytest` and a test database; set `ENV=test` to disable file logging in tests.

## Contributing & Notes

- Follow the repository pattern: routers -> schemas -> crud -> models.
- Prefer `async` DB calls and use the provided `get_async_session` dependency.
- Keep secrets out of source control; use `.env` or environment variables.
- When changing models, create an Alembic migration under `alembic/versions/`.

