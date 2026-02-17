"""
User Login Simulation Script.

This script simulates the user login process.
It authenticates the user using apps.sqlite.users.UserManager
and prints the session token if successful.
"""

import argparse
import os
import sys

# Add parent directory to path to allow imports from apps
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from apps.utils.logger import logger  # noqa: E402
from apps.sqlite.users import UserManager  # noqa: E402


def login_user(username, password):
    """Login a user and print the session token."""
    db_path = "data/database/haruquant.db"

    # Initialize UserManager
    user_manager = UserManager()
    user_manager.db_path = db_path

    try:
        print(f"Attempting to login user: {username}")

        session_token = user_manager.login_user(username, password)  # type: ignore

        if session_token:
            print("Login successful!")
            print(f"Session Token: {session_token}")
            return True
        else:
            print("Login failed. Check username and password.")
            return False

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        logger.exception("Login failed")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Simulate User Login")
    parser.add_argument("--username", help="Username", required=True)
    parser.add_argument("--password", help="Password", required=True)

    args = parser.parse_args()

    login_user(username=args.username, password=args.password)

