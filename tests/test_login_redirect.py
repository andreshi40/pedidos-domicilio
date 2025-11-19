import time
import requests
import pytest


FRONTEND = "http://localhost:5000"
GATEWAY = "http://localhost:8000/api/v1"


def _register_user(email: str, password: str):
    url = f"{GATEWAY}/auth/register"
    payload = {"email": email, "password": password, "role": "cliente"}
    try:
        r = requests.post(url, json=payload, timeout=5)
        return r
    except requests.exceptions.RequestException as e:
        pytest.skip(f"No se pudo contactar gateway para registrar usuario: {e}")


def test_login_redirect_to_client():
    # Preparar usuario único
    ts = int(time.time())
    email = f"testredir_{ts}@example.com"
    password = "testpassword123"

    # Registrar usuario vía gateway
    reg = _register_user(email, password)
    assert reg.status_code in (200, 201), (
        f"Registro falló: {reg.status_code} {reg.text}"
    )

    # Usar sesión para mantener cookies
    s = requests.Session()
    login_url = f"{FRONTEND}/login"
    # El frontend espera form data
    data = {"email": email, "password": password}

    try:
        resp = s.post(login_url, data=data, allow_redirects=False, timeout=5)
    except requests.exceptions.RequestException as e:
        pytest.skip(f"No se pudo contactar frontend para login: {e}")

    # Debe responder con redirect (302/303) hacia /client
    assert resp.status_code in (302, 303), (
        f"Login no redirigió, código {resp.status_code} body={resp.text[:200]}"
    )
    loc = resp.headers.get("Location", "")
    assert loc, f"Respuesta de login no incluyó Location header: {resp.headers}"
    assert loc.endswith("/client") or loc.endswith("/client/"), (
        f"Location esperada /client, se obtuvo: {loc}"
    )

    # Opcional: seguir la redirección y comprobar contenido
    follow = s.get(f"{FRONTEND}{loc}", timeout=5)
    assert follow.status_code == 200, (
        f"Al seguir redirect a {loc} se obtuvo {follow.status_code}"
    )
    assert "restaurantes" in follow.text.lower() or "buscar" in follow.text.lower(), (
        "La página destino no parece lista de restaurantes"
    )
