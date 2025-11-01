import os
import time
import requests

GATEWAY = os.getenv("GATEWAY_URL", "http://localhost:8000")
AUTH = os.getenv("AUTH_URL", "http://localhost:8001")

TEST_EMAIL = "gateway_test@example.com"
TEST_PWD = "test_pass_123"


def test_public_register_allowed():
    # Ensure register via gateway is allowed without Authorization
    resp = requests.post(f"{GATEWAY}/api/v1/auth/register", json={"email": TEST_EMAIL, "password": TEST_PWD})
    # 200 or 409 if user already exists are acceptable
    assert resp.status_code in (200, 409)


def test_protected_requires_auth():
    # Request to protected endpoint without token should be 401
    resp = requests.get(f"{GATEWAY}/api/v1/auth/me")
    assert resp.status_code == 401


def obtain_token():
    # Login via auth service to obtain access token
    resp = requests.post(f"{AUTH}/login", json={"email": TEST_EMAIL, "password": TEST_PWD})
    assert resp.status_code == 200
    import os
    import time
    import requests

    GATEWAY = os.getenv("GATEWAY_URL", "http://localhost:8000")
    AUTH = os.getenv("AUTH_URL", "http://localhost:8001")

    TEST_EMAIL = "gateway_test@example.com"
    TEST_PWD = "test_pass_123"


    def test_public_register_allowed():
        # Ensure register via gateway is allowed without Authorization
        resp = requests.post(f"{GATEWAY}/api/v1/auth/register", json={"email": TEST_EMAIL, "password": TEST_PWD})
        # 200 or 409 if user already exists are acceptable
        assert resp.status_code in (200, 409)


    def test_protected_requires_auth():
        # Request to protected endpoint without token should be 401
        resp = requests.get(f"{GATEWAY}/api/v1/auth/me")
        assert resp.status_code == 401


    def obtain_token():
        # Login via auth service to obtain access token
        resp = requests.post(f"{AUTH}/login", json={"email": TEST_EMAIL, "password": TEST_PWD})
        assert resp.status_code == 200
        data = resp.json()
        return data.get("access_token")


    def test_protected_with_valid_token():
        # Pause briefly in case services are still starting
        time.sleep(0.5)
        token = obtain_token()
        assert token
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{GATEWAY}/api/v1/auth/me", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "user" in data and data["user"].get("email") == TEST_EMAIL