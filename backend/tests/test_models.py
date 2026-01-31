import pytest
from app.models.user import User

def test_user_model():
    user = User(
        username="testuser",
        password_hash="hashed123",
        email="test@example.com"
    )
    assert user.username == "testuser"
    assert user.email == "test@example.com"
    assert user.is_active is True
