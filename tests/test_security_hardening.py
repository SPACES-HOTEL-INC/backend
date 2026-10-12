import pytest

from app.core.security import create_refresh_token, decode_token


def test_decode_token_rejects_wrong_token_type():
    token = create_refresh_token("user-123")

    with pytest.raises(ValueError):
        decode_token(token, expected_type="access")
