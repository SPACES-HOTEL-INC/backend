import hashlib
import hmac
import time
import uuid
from decimal import Decimal
from typing import Any

import httpx

from ..config import settings


def make_tx_ref(prefix: str = "spaces") -> str:
    """Build a transaction reference that is unique and human-readable."""
    stamp = int(time.time())
    random_part = uuid.uuid4().hex[:8]
    return f"{prefix}-{stamp}-{random_part}"


def verify_webhook_signature(payload: bytes | str, signature: str | None, secret: str) -> bool:
    """Validate Flutterwave webhook HMAC signatures against the configured secret."""
    if not secret or not signature:
        return False

    if isinstance(payload, str):
        payload_bytes = payload.encode("utf-8")
    else:
        payload_bytes = payload

    expected = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
    return hmac.compare_digest(signature.lower(), expected.lower())


def build_checkout_payload(
    *,
    amount: float | int | Decimal,
    currency: str,
    email: str,
    tx_ref: str,
    booking_id: str,
    user_id: str,
    payment_options: str = "card",
    redirect_url: str | None = None,
    customer_name: str | None = None,
    description: str = "Booking payment",
) -> dict[str, Any]:
    """Create a standard Flutterwave checkout payload for server-side initiation."""
    amount_value = float(amount)
    if amount_value.is_integer():
        amount_value = int(amount_value)

    return {
        "amount": amount_value,
        "currency": (currency or "NGN").upper(),
        "tx_ref": tx_ref,
        "redirect_url": redirect_url or "https://example.com/payment/callback",
        "payment_options": payment_options,
        "customer": {
            "email": email,
            "name": customer_name or email,
        },
        "customizations": {
            "title": "Spaces booking payment",
            "description": description,
            "logo": "https://example.com/logo.png",
        },
        "meta": {
            "booking_id": str(booking_id),
            "user_id": str(user_id),
        },
    }


def create_flutterwave_payment(payload: dict[str, Any]) -> dict[str, Any]:
    """Initialize a payment request against the Flutterwave API."""
    if not settings.FLW_SECRET_KEY:
        raise RuntimeError("FLW_SECRET_KEY is not configured")

    base_url = settings.FLW_BASE_URL.rstrip("/")
    headers = {
        "Authorization": f"Bearer {settings.FLW_SECRET_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        response = httpx.post(f"{base_url}/payments", json=payload, headers=headers, timeout=30)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text
        raise RuntimeError(f"Flutterwave rejected the payment request: {detail or exc}") from exc
    return response.json()


def verify_flutterwave_transaction(transaction_id: str | int) -> dict[str, Any]:
    """Look up the current gateway status for a payment reference."""
    if not settings.FLW_SECRET_KEY:
        raise RuntimeError("FLW_SECRET_KEY is not configured")

    base_url = settings.FLW_BASE_URL.rstrip("/")
    headers = {
        "Authorization": f"Bearer {settings.FLW_SECRET_KEY}",
        "Accept": "application/json",
    }

    response = httpx.get(f"{base_url}/transactions/{transaction_id}/verify", headers=headers, timeout=30)
    response.raise_for_status()
    return response.json()
