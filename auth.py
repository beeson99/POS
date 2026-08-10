"""
Authentication and user management for the POS system.
Wraps database calls with a clean interface.
"""
import database


def login(username, password):
    """
    Validate login credentials.
    Returns {"username": ..., "role": ...} dict on success, None on failure.
    """
    result = database.validate_login(username, password)
    if result:
        return {"username": username, "role": result[0]}
    return None


def get_display_name(username):
    """Return the display name for a user."""
    return database.get_user_name(username)


def is_manager(user):
    """Check if a user dict has manager role."""
    return user.get("role") == "manager"


def verify_manager(password):
    """Return manager username if password is valid for a manager, else None."""
    return database.verify_manager_password(password)


def verify_admin(password):
    """Return True if password matches the admin account."""
    return database.verify_admin_password(password)


def get_all_users():
    """Return list of (username, name, role) tuples."""
    return database.list_users()


def create_user(username, password, name, role):
    """Create a new user. Raises on duplicate username."""
    database.add_user(username, password, name, role)


def remove_user(username):
    """Delete a user by username."""
    database.delete_user(username)
