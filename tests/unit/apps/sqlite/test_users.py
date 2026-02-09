
import pytest
import sqlite3
import os
from apps.sqlite.users import UserManager
from apps.sqlite.schema import SchemaManager

@pytest.fixture
def db_path(tmp_path):
    # Create a compact temp db file
    d = tmp_path / "test.db"
    return str(d)

from unittest.mock import patch

@pytest.fixture
def user_manager(db_path):
    # Initialize Schema
    schema = SchemaManager()
    schema.db_path = db_path
    schema.initialize_database()
    
    # Mock password hashing to avoid environment issues with bcrypt/passlib on Python 3.14
    with patch("apps.sqlite.users.hash_password", side_effect=lambda p: f"hashed_{p}"), \
         patch("apps.sqlite.users.verify_password", side_effect=lambda p, h: h == f"hashed_{p}"):
        yield UserManager(db_path)

def test_create_user(user_manager):
    uid = user_manager.create_user(
        email="test@example.com",
        username="testuser",
        password="password123",
        full_name="Test User"
    )
    assert uid is not None
    assert uid > 0
    
    # Retrieve
    user = user_manager.get_user(uid)
    assert user["username"] == "testuser"
    assert user["email"] == "test@example.com"

def test_duplicate_user(user_manager):
    user_manager.create_user("u1@test.com", "u1", "pass")
    with pytest.raises(Exception): # UserAlreadyExistsError usually
        user_manager.create_user("u1@test.com", "u1", "pass")

def test_login(user_manager):
    user_manager.create_user("login@test.com", "loginuser", "secret")
    
    # Valid login
    token = user_manager.login_user("loginuser", "secret")
    assert token is not None
    
    # Invalid password
    assert user_manager.login_user("loginuser", "wrong") is None
    
    # Invalid user
    assert user_manager.login_user("nonexistent", "secret") is None

def test_session_management(user_manager):
    uid = user_manager.create_user("sess@test.com", "sessuser", "pass")
    token = user_manager.create_session(uid)
    
    assert token is not None
    
    # Get session
    session = user_manager.get_session(token)
    assert session is not None
    assert session["user_id"] == uid
    
    # Delete session
    assert user_manager.delete_session(token)
    assert user_manager.get_session(token) is None

def test_update_settings(user_manager):
    uid = user_manager.create_user("set@test.com", "setuser", "pass")
    
    new_settings = {
        "theme": "dark",
        "language": "ja"
    }
    assert user_manager.update_user_settings(uid, new_settings)
    
    settings = user_manager.get_user_settings(uid)
    assert settings["theme"] == "dark"
    assert settings["language"] == "ja"
