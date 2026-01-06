"""
User Registration Simulation Script.

This script simulates the user registration process as if performed through the UI.
It generates an encryption key using apps.utils.security and saves the user
to the database using apps.sqlite.users.UserManager.
"""

import argparse
import os
import sys

# Add parent directory to path to allow imports from apps
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from apps.logger import logger  # noqa: E402
from apps.sqlite.users import UserAlreadyExistsError, UserManager  # noqa: E402
from apps.utils.security import get_encryption_key  # noqa: E402


def register_user(username, email, password, full_name=None, is_superuser=False):
    """Register a new user in the database."""
    db_path = "data/database/haruquant.db"

    # Initialize UserManager
    user_manager = UserManager()
    user_manager.db_path = db_path

    try:
        print(f"Attempting to register user: {username} ({email})")

        # explicit encryption key generation as requested
        encryption_key = get_encryption_key()
        print("Generated new encryption key.")

        user_id = user_manager.create_user(
            email=email,
            username=username,
            password=password,
            full_name=full_name,
            is_superuser=is_superuser,
            encryption_key=encryption_key,
        )

        print(f"Successfully registered user '{username}' with ID: {user_id}")
        return True

    except UserAlreadyExistsError:
        print(f"Error: User '{username}' or email '{email}' already exists.")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        logger.exception("Registration failed")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate User Registration")
    parser.add_argument("--username", help="Username", default="sim_user")
    parser.add_argument("--email", help="Email address", default="sim_user@example.com")
    parser.add_argument("--password", help="Password", default="password123")
    parser.add_argument("--full-name", help="Full Name", default="Simulation User")
    parser.add_argument("--superuser", action="store_true", help="Create as superuser")

    args = parser.parse_args()

    register_user(
        username=args.username,
        email=args.email,
        password=args.password,
        full_name=args.full_name,
        is_superuser=args.superuser,
    )
