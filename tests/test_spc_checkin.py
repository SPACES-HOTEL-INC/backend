import uuid

from app.models.booking import Booking, BookingStatus


def test_booking_supports_checked_in_state_and_spc_code():
    booking = Booking(
        id=uuid.uuid4(),
        room_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        status=BookingStatus.CHECKED_IN,
        spc_code="SPC-AB12",
    )

    assert booking.status == BookingStatus.CHECKED_IN
    assert booking.spc_code == "SPC-AB12"
