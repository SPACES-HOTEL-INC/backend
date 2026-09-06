# API Reference — Spaces Backend

This file lists the main endpoints, expected request shapes, responses, and important behavior notes. Use the interactive OpenAPI docs at `/docs` while developing.

Authentication: most endpoints require a Bearer `access_token` in the `Authorization` header.

Common header for protected routes:

```
Authorization: Bearer <access_token>
```

---

## /api/v1/auth

- POST /register
  - Description: Create a new user account.
  - Body: `UserCreate` { "email", "password", "full_name"?, "phone_number"? }
  - Response: `UserRead` (201)

- POST /login
  - Description: Authenticate a user and receive tokens.
  - Body: `UserLogin` { "email", "password" }
  - Response: `Token` { "access_token", "refresh_token", "token_type" }

- POST /refresh
  - Description: Exchange refresh token (or use current user) for a new access token.
  - Body/Query: optional `refresh_token` string (or provide Bearer for current user)
  - Response: `Token`

---

## /api/v1/users

- GET /me
  - Auth: required
  - Response: `UserRead`

- PUT /me
  - Auth: required
  - Body: `UserUpdate` (partial allowed)
  - Response: `UserRead`

- GET / (list users)
  - Auth: admin-only

- GET /{user_id}
  - Auth: admin-only

---

## /api/v1/properties

- GET /
  - Params: `city`, `property_type`, `min_price`, `max_price`, `page`, `limit`
  - Response: list of `PropertyRead`

- GET /mine
  - Auth: required (host)
  - Response: list of `PropertyRead` owned by the user

- GET /{property_id}
  - Response: `PropertyRead`

- POST /
  - Auth: required
  - Content-Type: `multipart/form-data`
  - Form fields: `name`/`hotel_name`, `property_type`, `address`, `city`, `state`, `country`, `phone`, `email`, `description`, `amenities` (JSON string), `images` files
  - Behavior: tries Cloudinary upload; falls back to local `static/uploads/properties`.

- PUT /{property_id}
  - Auth: property owner
  - Body: `PropertyUpdate`

- DELETE /{property_id}
  - Auth: owner or admin — marks `is_active=false`

- PATCH /{property_id}/verify
  - Auth: admin — sets `is_verified=true`

---

## /api/v1/rooms

- GET /
  - Auth: `require_host`
  - Query: optional `property_id` to list rooms for a specific property

- POST / or /json
  - Auth: `require_host`
  - Body: `RoomCreate` { "title", "description", "price_per_night", "images": [str] }

- POST /upload
  - Auth: `require_host`
  - Content-Type: `multipart/form-data` with `title`, `description`, `price_per_night`, `property_id`, and `images` files
  - Requirements: between 3 and 7 images

---

## /api/v1/bookings

- POST /
  - Auth: required
  - Body: `BookingCreate` with `room_id`, `check_in_date`, `check_out_date`, `num_guests`, `total_price` etc.
  - Validations: `check_out_date` > `check_in_date`; cannot book past dates; ensures no conflicting bookings.

- GET /mine
  - Auth: required
  - Response: bookings for current guest

- GET /host-bookings
  - Auth: `require_host`
  - Response: bookings for host's properties

- GET /{booking_id}
  - Auth: owner or admin

- DELETE /{booking_id}
  - Auth: owner or admin — sets status to `cancelled`

---

## /api/v1/payments

- POST /initiate
  - Auth: required
  - Body: `PaymentCreate` { "booking_id", "amount", "payment_method" }
  - Behavior: creates payment record tied to a booking

- GET /mine
  - Auth: required — lists payments initiated by the current guest

- GET /{payment_id}
  - Auth: owner or admin

- POST /webhook
  - Description: payment provider webhook receiver
  - Header: `X-Webhook-Secret` must match `PAYMENT_WEBHOOK_SECRET` env var

---

## /api/v1/reviews

- POST /
  - Auth: required
  - Body: `ReviewCreate` { "booking_id", "rating", "comment" }
  - Preconditions: booking must exist, belong to user, and have status `completed`.

- GET /property/{property_id}
  - Response: list of `ReviewRead` for the property

- PUT /{review_id}
  - Auth: review author — `ReviewUpdate`

- POST /{review_id}/host-response
  - Auth: `require_host` — host may add `host_response`

- DELETE /{review_id}
  - Auth: admin-only — delete review

---

## Example: create property (curl)

```bash
curl -X POST "http://127.0.0.1:8000/api/v1/properties" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -F "name=Seaside Hotel" \
  -F "address=12 Beach Road" \
  -F "images=@room1.jpg" \
  -F "images=@room2.jpg" \
  -F "amenities=[\"wifi\",\"pool\"]"
```

