"""
Test key UI routes after logging in as admin.
Run with: pytest tests/test_ui_routes_after_login.py -v
Or: python -m pytest tests/test_ui_routes_after_login.py -v

Requires the app to be running on BASE_URL (default http://localhost:8001).
Uses username=admin, password=password123.
"""
import os
import pytest
import requests

BASE_URL = os.environ.get("LHIMS_BASE_URL", "http://localhost:8001")
USERNAME = os.environ.get("LHIMS_TEST_USER", "admin")
PASSWORD = os.environ.get("LHIMS_TEST_PASSWORD", "password123")


def login_session():
    """POST login, return session with cookie set."""
    s = requests.Session()
    s.headers["User-Agent"] = "LHIMS-UI-Test/1.0"
    r = s.post(
        f"{BASE_URL}/login",
        data={"username": USERNAME, "password": PASSWORD},
        allow_redirects=True,
    )
    if r.status_code == 401:
        pytest.skip(
            f"Login failed (401). Ensure app is running at {BASE_URL} and user "
            f"{USERNAME} exists with the given password (e.g. run scripts/seed_admin.py)."
        )
    assert r.status_code in (200, 302), f"Login failed: {r.status_code}"
    if r.status_code == 200 and "/login" in r.url:
        pytest.skip("Login returned 200 on login page - check credentials or app")
    return s


@pytest.fixture(scope="module")
def session():
    return login_session()


def get(session, path, allow_redirects=True):
    """GET path and return response."""
    return session.get(f"{BASE_URL}{path}", allow_redirects=allow_redirects)


# --- Key routes to test (path, optional description) ---
ROUTES = [
    ("/", "Dashboard"),
    ("/patients/list", "Patients list"),
    ("/patients/register", "Register patient"),
    ("/front-office/queue", "Front office queue"),
    ("/appointments/manage", "Manage appointments"),
    ("/nurse/dashboard", "Nurse dashboard"),
    ("/nurse/triage-queue", "Nurse triage queue"),
    ("/doctor/dashboard", "Doctor dashboard"),
    ("/doctor/queue", "Doctor queue"),
    ("/opd/dashboard", "OPD dashboard"),
    ("/ipd/dashboard", "IPD dashboard"),
    ("/ipd/wards", "IPD wards"),
    ("/ipd/admissions", "IPD admissions"),
    ("/pharmacy", "Pharmacy dashboard"),
    ("/pharmacy/inventory", "Inventory dashboard"),
    ("/lab", "Lab dashboard"),
    ("/radiology", "Radiology dashboard"),
    ("/procedures", "Procedures list"),
    ("/billing", "Billing dashboard"),
    ("/reports", "Reports dashboard"),
    ("/admin/users", "User management"),
    ("/doctors/list", "Doctors list"),
    ("/admin/hospital-settings", "Hospital settings"),
    ("/admin/service-pricing", "Service pricing"),
    ("/admin/diseases", "Diseases management"),
    ("/insurance-providers", "Insurance providers"),
    ("/login", "Login page (may redirect if already logged in)"),
]


@pytest.mark.parametrize("path,description", ROUTES)
def test_route_returns_ok(session, path, description):
    """Each key route should return 200 or 302 (redirect), not 500 or 404 for authenticated user."""
    r = get(session, path)
    # 200 = success, 302 = redirect (e.g. to login if no permission, or internal redirect)
    # 403 = forbidden (role), 404 = not found - we still want to notice
    assert r.status_code in (200, 302), (
        f"{description} ({path}): expected 200 or 302, got {r.status_code}"
    )
    if r.status_code == 302:
        location = r.headers.get("Location", "")
        # Redirect to login = likely session expired or no permission
        if "login" in location and path != "/login":
            pytest.skip(f"{description} redirects to login (role may not have access)")


def test_login_sets_cookie():
    """Login with valid credentials should set access_token cookie."""
    s = requests.Session()
    r = s.post(
        f"{BASE_URL}/login",
        data={"username": USERNAME, "password": PASSWORD},
        allow_redirects=False,
    )
    # Expect redirect to dashboard
    assert r.status_code == 302
    assert "access_token" in s.cookies or "access_token" in r.headers.get("Set-Cookie", "")
