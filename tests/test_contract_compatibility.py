import uuid
from datetime import date

from sqlalchemy.dialects import postgresql

from app.models.property import Property
from app.models.user import UserRole, UserRoleType
from app.schemas.booking import BookingCreate
from app.schemas.property import PropertyCreate
from app.schemas.support import SupportTicketCreate, SupportTicketRead


def test_property_model_exposes_host_id_alias():
    owner_id = uuid.uuid4()
    property_obj = Property(owner_id=owner_id)

    assert property_obj.host_id == owner_id
    property_obj.host_id = uuid.uuid4()
    assert property_obj.owner_id == property_obj.host_id


def test_booking_create_accepts_legacy_date_fields():
    booking = BookingCreate(
        room_id=uuid.uuid4(),
        property_id=uuid.uuid4(),
        check_in_date=date(2099, 1, 1),
        check_out_date=date(2099, 1, 3),
        num_guests=2,
        total_price=240.0,
    )

    assert booking.check_in == date(2099, 1, 1)
    assert booking.check_out == date(2099, 1, 3)
    assert booking.total_price == 240.0


def test_property_create_schema_supports_current_api_fields():
    property_in = PropertyCreate(
        hotel_name="Ocean View",
        description="Nice place",
        property_type="hotel",
        address="Lagos",
        city="Lagos",
        state="Lagos",
        country="Nigeria",
        images=[],
    )

    assert property_in.hotel_name == "Ocean View"
    assert property_in.city == "Lagos"
    assert property_in.state == "Lagos"


def test_user_roles_remain_compatible_with_host_and_admin_access():
    assert UserRole.HOST == "host"
    assert UserRole.ADMIN == "admin"
    assert UserRole.CONSUMER == "consumer"


def test_user_role_type_binds_expected_postgresql_enum_values():
    dialect = postgresql.dialect()
    role_type = UserRoleType()
    processor = role_type.bind_processor(dialect)

    assert processor(UserRole.CONSUMER) == "CONSUMER"
    assert processor(UserRole.HOST) == "HOTEL"
    assert processor(UserRole.ADMIN) == "ADMIN"


def test_support_ticket_schema_matches_frontend_contract():
    created = SupportTicketCreate(subject="Payout delayed", message="My payout is delayed")

    assert created.subject == "Payout delayed"
    assert created.message == "My payout is delayed"

    payload = SupportTicketRead(
        id="TKT-1042",
        subject="Payout delayed",
        date="Sep 20, 2026",
        status="In Progress",
    )

    assert payload.model_dump() == {
        "id": "TKT-1042",
        "subject": "Payout delayed",
        "date": "Sep 20, 2026",
        "status": "In Progress",
    }
