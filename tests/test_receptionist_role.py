from app.models.user import User, UserRole


def test_receptionist_role_is_recognized():
    assert UserRole.coerce("receptionist") == UserRole.RECEPTIONIST
    assert UserRole.coerce("reception") == UserRole.RECEPTIONIST


def test_user_can_hold_receptionist_role():
    user = User(email="staff@example.com", hashed_password="hash")
    user.role = UserRole.RECEPTIONIST
    assert user.role == UserRole.RECEPTIONIST
    assert user.has_role(UserRole.RECEPTIONIST)
    assert user.is_host is False
    assert user.is_admin is False
