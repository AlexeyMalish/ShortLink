from datetime import timedelta
from src.auth import verify_password, get_password_hash, create_access_token


def test_verify_password():
    password = "password"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed) is True
    assert verify_password("wrong_password", hashed) is False


def test_create_access_token():
    token = create_access_token({"sub": "hse@example.com"})
    assert isinstance(token, str)

    token_with_expire = create_access_token(
        {"sub": "hse@example.com"},
        timedelta(minutes=30))
    assert isinstance(token_with_expire, str)
