import hashlib
import hmac

from app.core.flutterwave import build_checkout_payload, verify_webhook_signature


def test_verify_webhook_signature_accepts_valid_hash():
    payload = b'{"event":"charge.completed","data":{"id":123}}'
    secret = "super-secret"
    signature = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()

    assert verify_webhook_signature(payload, signature, secret) is True
    assert verify_webhook_signature(payload, "bad-signature", secret) is False


def test_build_checkout_payload_includes_booking_and_reference():
    payload = build_checkout_payload(
        amount=2500,
        currency="NGN",
        email="guest@example.com",
        tx_ref="spaces-123",
        booking_id="b6a7c5a2-7b90-4d94-90b1-23a7b23ff2bd",
        user_id="6d97d66b-c6d8-44c8-9f92-ee4e7b1d7121",
    )

    assert payload["amount"] == 2500
    assert payload["currency"] == "NGN"
    assert payload["tx_ref"] == "spaces-123"
    assert payload["customer"]["email"] == "guest@example.com"
    assert payload["meta"]["booking_id"] == "b6a7c5a2-7b90-4d94-90b1-23a7b23ff2bd"
