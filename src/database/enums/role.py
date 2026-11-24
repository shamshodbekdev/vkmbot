from enum import Enum


class UserRole(str, Enum):
    USER = "user"
    ADMINISTRATOR = "admin"
    # Stored as "mod": the existing users.role column is varchar(5).
    MODERATOR = "mod"


# Roles that can open the admin panel (the superadmin is TELEGRAM_ID in .env).
STAFF_ROLES = (UserRole.ADMINISTRATOR, UserRole.MODERATOR)
