"""
Usage examples for apps.sqlite.users.py

This module demonstrates:
- UserManager class for user CRUD operations
- User creation with password hashing
- User settings management
- MT5 credentials retrieval
"""

from apps.sqlite import SQLiteDatabase, UserAlreadyExistsError


def example_create_user():
    """
    Example: Creating a new user

    Creates a user with:
    - Email (must be unique)
    - Username (must be unique)
    - Password (automatically hashed)
    - Optional: full_name, is_superuser, encryption_key
    """
    db = SQLiteDatabase(db_path="test_users.db")
    db.initialize_database()

    # Create a regular user
    user_id = db.create_user(
        email="trader@example.com",
        username="trader123",
        password="secure_password",
        full_name="John Trader"
    )
    print(f"User created with ID: {user_id}")

    # Create a superuser
    admin_id = db.create_user(
        email="admin@example.com",
        username="admin",
        password="admin_password",
        full_name="System Administrator",
        is_superuser=True
    )
    print(f"Superuser created with ID: {admin_id}")


def example_handle_duplicate_user():
    """
    Example: Handling UserAlreadyExistsError

    Attempting to create a user with duplicate email or username
    raises UserAlreadyExistsError.
    """
    db = SQLiteDatabase(db_path="test_duplicate.db")
    db.initialize_database()

    # First user creation succeeds
    user_id = db.create_user(
        email="test@example.com",
        username="testuser",
        password="password123"
    )
    print(f"First user created: {user_id}")

    # Attempt to create user with same username
    try:
        db.create_user(
            email="different@example.com",
            username="testuser",  # Duplicate username
            password="password456"
        )
    except UserAlreadyExistsError as e:
        print(f"Error: {e}")
        print("Handled duplicate username error")

    # Attempt to create user with same email
    try:
        db.create_user(
            email="test@example.com",  # Duplicate email
            username="differentuser",
            password="password789"
        )
    except UserAlreadyExistsError as e:
        print(f"Error: {e}")
        print("Handled duplicate email error")


def example_get_user():
    """
    Example: Retrieving user information

    Users can be retrieved by:
    - user_id
    - username
    - email
    """
    db = SQLiteDatabase(db_path="test_get_user.db")
    db.initialize_database()

    # Create a user
    user_id = db.create_user(
        email="retrieve@example.com",
        username="retriever",
        password="password123",
        full_name="Data Retriever"
    )

    # Get user by ID
    user = db.get_user(user_id=user_id)
    print(f"\nUser by ID: {user['username']} - {user['email']}")

    # Get user by username
    user = db.get_user(username="retriever")
    print(f"User by username: {user['full_name']} (ID: {user['id']})")

    # Get user by email
    user = db.get_user(email="retrieve@example.com")
    print(f"User by email: {user['username']} (Active: {user['is_active']})")

    # Attempt to get non-existent user
    user = db.get_user(username="nonexistent")
    if user is None:
        print("\nNon-existent user returns None")


def example_update_user():
    """
    Example: Updating user information

    Can update:
    - email, username, full_name
    - is_active, is_superuser, is_verified
    - password (automatically hashed)
    - last_login
    """
    db = SQLiteDatabase(db_path="test_update_user.db")
    db.initialize_database()

    # Create a user
    user_id = db.create_user(
        email="old@example.com",
        username="olduser",
        password="oldpassword"
    )

    # Update email and username
    db.update_user(
        user_id=user_id,
        email="new@example.com",
        username="newuser"
    )
    print("Updated email and username")

    # Update full name
    db.update_user(
        user_id=user_id,
        full_name="New Name"
    )
    print("Updated full name")

    # Update password
    db.update_user(
        user_id=user_id,
        password="newpassword"  # Will be hashed automatically
    )
    print("Updated password (hashed)")

    # Deactivate user
    db.update_user(
        user_id=user_id,
        is_active=False
    )
    print("Deactivated user")

    # Verify user
    db.update_user(
        user_id=user_id,
        is_verified=True
    )
    print("Verified user")

    # Get updated user
    user = db.get_user(user_id=user_id)
    print(f"\nFinal user state:")
    print(f"  Email: {user['email']}")
    print(f"  Username: {user['username']}")
    print(f"  Full Name: {user['full_name']}")
    print(f"  Active: {user['is_active']}")
    print(f"  Verified: {user['is_verified']}")


def example_delete_user():
    """
    Example: Deleting a user

    Deleting a user cascades to:
    - User settings
    - Strategies
    - Backtest runs
    - Live trading sessions
    """
    db = SQLiteDatabase(db_path="test_delete_user.db")
    db.initialize_database()

    # Create a user
    user_id = db.create_user(
        email="deleteme@example.com",
        username="deleteme",
        password="password123"
    )
    print(f"User created: {user_id}")

    # Verify user exists
    user = db.get_user(user_id=user_id)
    print(f"User exists: {user['username']}")

    # Delete user
    success = db.delete_user(user_id=user_id)
    print(f"\nUser deleted: {success}")

    # Verify user no longer exists
    user = db.get_user(user_id=user_id)
    print(f"User exists after delete: {user is not None}")


def example_user_settings():
    """
    Example: Managing user settings

    User settings include:
    - theme, language, timezone
    - log_verbosity, performance_mode
    - broker_credentials, trading_preferences
    - notifications, alert_triggers
    """
    db = SQLiteDatabase(db_path="test_settings.db")
    db.initialize_database()

    # Create a user (settings created automatically)
    user_id = db.create_user(
        email="settings@example.com",
        username="settingsuser",
        password="password123"
    )

    # Get default settings
    settings = db.get_user_settings(user_id)
    print("Default settings:")
    print(f"  Theme: {settings['theme']}")
    print(f"  Language: {settings['language']}")
    print(f"  Timezone: {settings['timezone']}")
    print(f"  Log Verbosity: {settings['log_verbosity']}")

    # Update settings
    db.update_user_settings(user_id, {
        "theme": "dark",
        "language": "en",
        "timezone": "America/New_York",
        "log_verbosity": "debug",
        "performance_mode": "high"
    })
    print("\nSettings updated")

    # Get updated settings
    settings = db.get_user_settings(user_id)
    print("Updated settings:")
    print(f"  Theme: {settings['theme']}")
    print(f"  Language: {settings['language']}")
    print(f"  Timezone: {settings['timezone']}")
    print(f"  Performance Mode: {settings['performance_mode']}")


def example_broker_credentials():
    """
    Example: Managing broker credentials in user settings

    Broker credentials are stored as JSON in user_settings.
    Includes methods to retrieve MT5 credentials.
    """
    db = SQLiteDatabase(db_path="test_credentials.db")
    db.initialize_database()

    # Create a user
    user_id = db.create_user(
        email="broker@example.com",
        username="brokeruser",
        password="password123"
    )

    # Add broker credentials
    broker_credentials = {
        "accounts": [
            {
                "name": "MT5 Demo",
                "login": 12345678,
                "password": "mt5password",
                "server": "Broker-Demo",
                "terminalPath": "C:/Program Files/MetaTrader 5",
                "isDefault": True
            },
            {
                "name": "MT5 Live",
                "login": 87654321,
                "password": "livepassword",
                "server": "Broker-Live",
                "terminalPath": "C:/Program Files/MetaTrader 5",
                "isDefault": False
            }
        ]
    }

    db.update_user_settings(user_id, {
        "broker_credentials": broker_credentials
    })
    print("Broker credentials saved")

    # Retrieve default MT5 credentials
    mt5_creds = db.get_mt5_credentials(user_id)
    if mt5_creds:
        print(f"\nDefault MT5 account:")
        print(f"  Login: {mt5_creds['login']}")
        print(f"  Server: {mt5_creds['server']}")
        print(f"  Path: {mt5_creds['path']}")

    # Retrieve specific account by login
    specific_creds = db.get_mt5_credentials_by_login(user_id, 87654321)
    if specific_creds:
        print(f"\nSpecific MT5 account (87654321):")
        print(f"  Login: {specific_creds['login']}")
        print(f"  Server: {specific_creds['server']}")


def example_trading_preferences():
    """
    Example: Managing trading preferences

    Trading preferences can include:
    - Default risk per trade
    - Preferred symbols/timeframes
    - Trading hours
    - Custom settings
    """
    db = SQLiteDatabase(db_path="test_preferences.db")
    db.initialize_database()

    # Create a user
    user_id = db.create_user(
        email="prefs@example.com",
        username="prefsuser",
        password="password123"
    )

    # Set trading preferences
    trading_prefs = {
        "default_risk_pct": 1.0,
        "default_symbols": ["EURUSD", "GBPUSD", "USDJPY"],
        "default_timeframe": "H1",
        "max_concurrent_trades": 3,
        "trading_hours": {
            "start": "09:00",
            "end": "17:00",
            "timezone": "America/New_York"
        }
    }

    db.update_user_settings(user_id, {
        "trading_preferences": trading_prefs
    })
    print("Trading preferences saved")

    # Retrieve preferences
    settings = db.get_user_settings(user_id)
    prefs = settings["trading_preferences"]
    print(f"\nTrading preferences:")
    print(f"  Risk per trade: {prefs['default_risk_pct']}%")
    print(f"  Symbols: {', '.join(prefs['default_symbols'])}")
    print(f"  Timeframe: {prefs['default_timeframe']}")
    print(f"  Max trades: {prefs['max_concurrent_trades']}")


def example_complete_user_lifecycle():
    """
    Example: Complete user lifecycle

    Shows the typical workflow:
    1. Create user
    2. Configure settings
    3. Add broker credentials
    4. Update user info over time
    5. Delete user when needed
    """
    db = SQLiteDatabase(db_path="test_lifecycle.db")
    db.initialize_database()

    print("Step 1: Create user")
    user_id = db.create_user(
        email="lifecycle@example.com",
        username="lifecycleuser",
        password="password123",
        full_name="Lifecycle User"
    )
    print(f"  User ID: {user_id}")

    print("\nStep 2: Configure settings")
    db.update_user_settings(user_id, {
        "theme": "dark",
        "language": "en",
        "timezone": "UTC"
    })
    print("  Settings configured")

    print("\nStep 3: Add broker credentials")
    db.update_user_settings(user_id, {
        "broker_credentials": {
            "accounts": [{
                "name": "Demo",
                "login": 12345,
                "password": "demo123",
                "server": "Broker-Demo",
                "terminalPath": "C:/MT5",
                "isDefault": True
            }]
        }
    })
    print("  Broker credentials added")

    print("\nStep 4: Update user profile")
    db.update_user(
        user_id=user_id,
        full_name="Updated Name",
        is_verified=True
    )
    print("  Profile updated")

    print("\nStep 5: User info summary")
    user = db.get_user(user_id=user_id)
    settings = db.get_user_settings(user_id)
    print(f"  Name: {user['full_name']}")
    print(f"  Email: {user['email']}")
    print(f"  Verified: {user['is_verified']}")
    print(f"  Theme: {settings['theme']}")

    print("\nStep 6: Delete user")
    success = db.delete_user(user_id=user_id)
    print(f"  Deleted: {success}")


if __name__ == "__main__":
    print("=" * 80)
    print("UserManager Usage Examples")
    print("=" * 80)

    print("\n1. Create User")
    print("-" * 80)
    example_create_user()

    print("\n2. Handle Duplicate User")
    print("-" * 80)
    example_handle_duplicate_user()

    print("\n3. Get User")
    print("-" * 80)
    example_get_user()

    print("\n4. Update User")
    print("-" * 80)
    example_update_user()

    print("\n5. Delete User")
    print("-" * 80)
    example_delete_user()

    print("\n6. User Settings")
    print("-" * 80)
    example_user_settings()

    print("\n7. Broker Credentials")
    print("-" * 80)
    example_broker_credentials()

    print("\n8. Trading Preferences")
    print("-" * 80)
    example_trading_preferences()

    print("\n9. Complete User Lifecycle")
    print("-" * 80)
    example_complete_user_lifecycle()
