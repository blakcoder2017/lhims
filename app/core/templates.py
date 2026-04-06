"""
Shared Jinja2Templates configuration for LHIMS.
This module exports a configured templates object with has_permission registered.
"""
from fastapi.templating import Jinja2Templates
from datetime import date, datetime

# Initialize Jinja2Templates
templates = Jinja2Templates(directory="app/templates")

# Get the Jinja2 environment explicitly
env = templates.env


# Register the age filter
def calculate_age(dob):
    """Calculate age from date of birth."""
    if not dob:
        return None
    if isinstance(dob, str):
        dob = date.fromisoformat(dob)
    today = date.today()
    age = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1
    return age


env.filters["age"] = calculate_age


def normalize_logo_url(url):
    """Convert legacy /static/uploads/logos/... to /uploads/logos/... for correct serving."""
    if not url or not isinstance(url, str):
        return url
    if url.startswith("/static/uploads/logos/"):
        return "/uploads/logos/" + url[len("/static/uploads/logos/"):]
    return url


env.filters["normalize_logo_url"] = normalize_logo_url


# Register has_permission filter for template permission checking
def has_permission_filter(user, permission_name):
    """Check if user has a specific permission."""
    if not user or not user.role:
        return False
    # Admin has all permissions
    if user.role.name and user.role.name.lower() == "admin":
        return True
    # Check if permission exists in user's permissions
    if user.role.permissions:
        return any(perm.name == permission_name for perm in user.role.permissions)
    return False


# Register globals
env.globals["has_permission"] = has_permission_filter
env.globals["today"] = date.today
env.globals["now"] = datetime.now  # Callable for templates to use now()
env.globals["datetime"] = datetime  # For templates to use datetime.now()

# Sync the filters and globals to templates.env for backwards compatibility
templates.env.filters = env.filters
templates.env.globals = env.globals
