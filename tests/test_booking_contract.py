import uuid
from datetime import date, datetime, timezone

from app.models.booking import Booking, BookingStatus
from app.models.room import Room
from app.schemas.booking import BookingRead


def test_booking_read_populates_property_and_date_fields_from_model():
    booking = Booking(
        id=uuid.uuid4(),
        room_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        status=BookingStatus.PENDING,
        check_in=date(2026, 10, 21),
        check_out=date(2026, 10, 22),
        total_price=60000,
        created_at=datetime.now(timezone.utc),
    )
    booking.room = Room(
        id=uuid.uuid4(),
        property_id=uuid.uuid4(),
        title="Suite",
        description="Description",
        price_per_night=200.0,
        images=[],
    )

    result = BookingRead.model_validate(booking)

    assert result.property_id == booking.room.property_id
    assert result.check_in_date == booking.check_in
    assert result.check_out_date == booking.check_out
