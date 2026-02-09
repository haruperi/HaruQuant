
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from fastapi import HTTPException
from apps.api.auth_utils import generate_token, verify_token, invalidate_token, authenticate_user, get_user_id_from_token

@pytest.fixture
def mock_db_manager():
    return MagicMock()

def test_generate_token(mock_db_manager):
    user_id = 1
    mock_db_manager.create_session.return_value = "test_token"
    
    token = generate_token(user_id, mock_db_manager)
    
    mock_db_manager.delete_user_sessions.assert_called_once_with(user_id)
    mock_db_manager.create_session.assert_called_once_with(user_id, duration_hours=24)
    assert token == "test_token"

def test_verify_token_valid(mock_db_manager):
    token = "valid_token"
    future_time = (datetime.now() + timedelta(hours=1)).isoformat()
    mock_db_manager.get_session.return_value = {
        "expire_time": future_time,
        "user_id": 123
    }
    
    user_id = verify_token(token, mock_db_manager)
    
    assert user_id == 123
    mock_db_manager.delete_session.assert_not_called()

def test_verify_token_expired(mock_db_manager):
    token = "expired_token"
    past_time = (datetime.now() - timedelta(hours=1)).isoformat()
    mock_db_manager.get_session.return_value = {
        "expire_time": past_time,
        "user_id": 123
    }
    
    user_id = verify_token(token, mock_db_manager)
    
    assert user_id is None
    mock_db_manager.delete_session.assert_called_once_with(token)

def test_verify_token_not_found(mock_db_manager):
    token = "unknown_token"
    mock_db_manager.get_session.return_value = None
    
    user_id = verify_token(token, mock_db_manager)
    
    assert user_id is None

def test_invalidate_token(mock_db_manager):
    token = "test_token"
    invalidate_token(token, mock_db_manager)
    mock_db_manager.delete_session.assert_called_once_with(token)

@patch('apps.api.auth_utils.verify_password')
def test_authenticate_user_success(mock_verify_password, mock_db_manager):
    username = "testuser"
    password = "password"
    user_data = {
        "id": 1,
        "email": "test@example.com",
        "username": username,
        "full_name": "Test User",
        "hashed_password": "hashed_password",
        "is_active": True,
        "is_verified": True
    }
    mock_db_manager.get_user.return_value = user_data
    mock_verify_password.return_value = True
    
    result = authenticate_user(username, password, mock_db_manager)
    
    assert result["status"] == "success"
    assert result["user"]["id"] == 1
    mock_db_manager.update_user.assert_called_once()

@patch('apps.api.auth_utils.verify_password')
def test_authenticate_user_invalid_password(mock_verify_password, mock_db_manager):
    mock_db_manager.get_user.return_value = {"hashed_password": "hashed"}
    mock_verify_password.return_value = False
    
    result = authenticate_user("user", "wrong", mock_db_manager)
    
    assert result["status"] == "invalid"
    assert result["user"] is None

def test_get_user_id_from_token_success():
    with patch('apps.api.auth_utils.DatabaseManager') as MockDB:
        with patch('apps.api.auth_utils.verify_token') as mock_verify:
            mock_verify.return_value = 123
            
            user_id = get_user_id_from_token("Bearer valid_token")
            
            assert user_id == 123
            mock_verify.assert_called_once()

def test_get_user_id_from_token_missing_header():
    with pytest.raises(HTTPException) as exc:
        get_user_id_from_token(None)
    assert exc.value.status_code == 401

def test_get_user_id_from_token_invalid():
    with patch('apps.api.auth_utils.DatabaseManager') as MockDB:
        with patch('apps.api.auth_utils.verify_token') as mock_verify:
            mock_verify.return_value = None
            
            with pytest.raises(HTTPException) as exc:
                get_user_id_from_token("Bearer invalid")
            assert exc.value.status_code == 401
