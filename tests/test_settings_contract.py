from app.schemas.settings import (
    BusinessSettingsRead,
    PasswordUpdateRequest,
    PreferencesRead,
    ProfileSettingsRead,
)


def test_profile_schema_uses_frontend_contract_names():
    payload = ProfileSettingsRead(
        id="usr_12345",
        fullName="Abubakar Samuel",
        email="samuel@example.com",
        phone="+2348059780405",
        role="Super Admin",
    )

    assert payload.model_dump(by_alias=True) == {
        "id": "usr_12345",
        "fullName": "Abubakar Samuel",
        "email": "samuel@example.com",
        "phone": "+2348059780405",
        "avatarUrl": "https://res.cloudinary.com/demo/image/upload/v1/avatar.jpg",
        "role": "Super Admin",
    }


def test_business_and_preferences_schemas_match_ui_contract():
    business = BusinessSettingsRead(
        propertyName="Spaces Hotel & Suites",
        businessEmail="contact@spaceshm.com",
        supportPhone="+2348059780405",
        address="123 Hospitality Way, Abuja, Nigeria",
        currency="NGN",
        timezone="Africa/Lagos",
        logoUrl="https://res.cloudinary.com/demo/image/upload/v1/logo.png",
    )
    prefs = PreferencesRead(
        emailNotifications=True,
        smsAlerts=False,
        bookingConfirmations=True,
        payoutAlerts=True,
        theme="dark",
    )

    assert business.model_dump(by_alias=True)["propertyName"] == "Spaces Hotel & Suites"
    assert prefs.model_dump(by_alias=True)["theme"] == "dark"


def test_password_update_schema_requires_match_and_password_strength():
    payload = PasswordUpdateRequest(
        currentPassword="OldPassword123!",
        newPassword="NewSecurePassword456!",
        confirmPassword="NewSecurePassword456!",
    )

    assert payload.currentPassword == "OldPassword123!"
    assert payload.newPassword == "NewSecurePassword456!"
