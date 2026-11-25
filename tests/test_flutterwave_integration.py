import asyncio
import hashlib
import hmac
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

from app.core.flutterwave import build_checkout_payload, verify_webhook_signature
from app.models.payment import Payment, PaymentStatus
from app.routers.payments import apply_payment_status, payment_callback


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


def test_verify_webhook_signature_accepts_flutterwave_verif_hash():
    payload = b'{"event":"charge.completed","data":{"tx_ref":"spaces-123"}}'
    secret = "flutterwave-dashboard-secret"

    assert verify_webhook_signature(payload, secret, secret) is True


def test_apply_payment_status_success_is_idempotent():
    payment = Payment(
        id=uuid.uuid4(),
        booking_id=uuid.uuid4(),
        amount=2500,
        currency="NGN",
        payment_method="flutterwave",
        status=PaymentStatus.pending,
    )
    session = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    async def run():
        with patch("app.routers.payments.hold_booking_wallet_funds", new=AsyncMock()) as hold:
            await apply_payment_status(session, payment, "successful", {"event": "charge.completed"})
            await apply_payment_status(session, payment, "success", {"event": "charge.completed"})
            assert hold.await_count == 1

    asyncio.run(run())
    assert payment.status == PaymentStatus.success
    assert payment.paid_at is not None


def test_apply_payment_status_handles_failed_and_refunded():
    payment = Payment(
        id=uuid.uuid4(),
        booking_id=uuid.uuid4(),
        amount=2500,
        currency="NGN",
        payment_method="flutterwave",
        status=PaymentStatus.pending,
    )
    session = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    async def run():
        await apply_payment_status(session, payment, "failed", {"event": "charge.failed"})
        assert payment.status == PaymentStatus.failed

        with patch("app.routers.payments.hold_booking_wallet_funds", new=AsyncMock()) as hold:
            await apply_payment_status(session, payment, "success", {"event": "charge.completed"})
            assert hold.await_count == 1

        with patch("app.routers.payments.reverse_booking_wallet_hold", new=AsyncMock()) as reverse:
            await apply_payment_status(session, payment, "refunded", {"event": "charge.refunded"})
            assert reverse.await_count == 1

    asyncio.run(run())
    assert payment.status == PaymentStatus.refunded
    assert payment.paid_at is None


def test_payment_callback_verifies_signature_and_updates_payment():
    payment = Payment(
        id=uuid.uuid4(),
        booking_id=uuid.uuid4(),
        amount=2500,
        currency="NGN",
        payment_method="flutterwave",
        status=PaymentStatus.pending,
    )
    session = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    payload = {"event": "charge.completed", "data": {"tx_ref": "spaces-123"}}

    async def run():
        with patch("app.routers.payments.hold_booking_wallet_funds", new=AsyncMock()) as hold:
            await apply_payment_status(session, payment, "successful", payload)
            assert hold.await_count == 1

    asyncio.run(run())
    assert payment.status == PaymentStatus.success
    assert payment.paid_at is not None


def test_payment_callback_verifies_and_updates_payment():
    payment = Payment(
        id=uuid.uuid4(),
        booking_id=uuid.uuid4(),
        amount=2500,
        currency="NGN",
        payment_method="flutterwave",
        status=PaymentStatus.pending,
        transaction_ref="spaces-123",
    )
    session = MagicMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    async def run():
        with (
            patch("app.routers.payments.get_payment_by_transaction_ref", new=AsyncMock(return_value=payment)),
            patch(
                "app.routers.payments.verify_flutterwave_transaction",
                return_value={"status": "success", "data": {"status": "successful", "tx_ref": "spaces-123"}},
            ),
            patch("app.routers.payments.hold_booking_wallet_funds", new=AsyncMock()),
        ):
            payload = {"event": "charge.completed", "data": {"tx_ref": "spaces-123"}}

            await apply_payment_status(session, payment, "successful", payload)
        assert payment.status == PaymentStatus.success
        assert payment.paid_at is not None

    asyncio.run(run())
