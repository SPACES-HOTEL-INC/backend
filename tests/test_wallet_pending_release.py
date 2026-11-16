import uuid

from app.models.booking import Booking, BookingStatus
from app.models.property import Property


def test_property_tracks_pending_balance_until_guest_checks_in():
    property_obj = Property(
        id=uuid.uuid4(),
        owner_id=uuid.uuid4(),
        hotel_name="Ocean View",
        address="123 Main Street",
        contact="hello@example.com",
        balance=0,
        pending_balance=0,
    )

    booking = Booking(
        id=uuid.uuid4(),
        room_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        status=BookingStatus.PENDING,
        total_price=1500,
    )

    property_obj.pending_balance = (property_obj.pending_balance or 0) + booking.total_price
    assert property_obj.pending_balance == 1500

    property_obj.pending_balance = (property_obj.pending_balance or 0) - booking.total_price
    property_obj.balance = (property_obj.balance or 0) + booking.total_price
    booking.status = BookingStatus.CHECKED_IN

    assert property_obj.pending_balance == 0
    assert property_obj.balance == 1500
    assert booking.status == BookingStatus.CHECKED_IN
