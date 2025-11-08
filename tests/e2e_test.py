#!/usr/bin/env python3
"""E2E smoke test (minimal) for pedidos-domicilio.

Flow:
 - register a test user via API Gateway
 - login and get access_token
 - fetch frontend /client HTML and ensure restaurants are listed
 - visit a restaurant detail page on the frontend
 - fetch menu via gateway and create a pedido using the gateway with the token
 - fetch the pedido and assert a repartidor was assigned

Requirements: Python 3, requests
"""
import requests
import re
import sys
import time
from uuid import uuid4

FRONTEND = "http://localhost:5000"
GATEWAY = "http://localhost:8000"


def fail(msg, code=1):
    print("ERROR:", msg)
    sys.exit(code)


def main():
    ts = int(time.time())
    email = f"e2e_{ts}_{uuid4().hex[:6]}@example.com"
    password = "password123"

    print("1) Registering user", email)
    r = requests.post(f"{GATEWAY}/api/v1/auth/register", json={"email": email, "password": password, "role": "cliente"}, timeout=5)
    if r.status_code not in (200, 201):
        fail(f"register failed: {r.status_code} {r.text}")
    print("  registered")

    print("2) Logging in")
    r = requests.post(f"{GATEWAY}/api/v1/auth/login", json={"email": email, "password": password}, timeout=5)
    if r.status_code != 200:
        fail(f"login failed: {r.status_code} {r.text}")
    token = r.json().get("access_token")
    if not token:
        fail("no access_token returned")
    headers = {"Authorization": f"Bearer {token}"}
    print("  got token")

    print("3) Load frontend /client and check restaurant list")
    r = requests.get(f"{FRONTEND}/client", timeout=5)
    if r.status_code != 200:
        fail(f"frontend /client failed: {r.status_code}")
    html = r.text
    # simple check for known restaurants
    if not re.search(r"La Pizzeria|Sushi Express|Taco House", html, re.I):
        fail("restaurant names not found in frontend HTML")
    print("  frontend shows restaurants")

    # extract first restaurant link
    m = re.search(r'href="(/restaurants/[^"]+)"', html)
    if not m:
        fail("could not find restaurant link in frontend HTML")
    rest_path = m.group(1)
    rest_id = rest_path.split('/')[-1]
    print(f"  using restaurant: {rest_id}")

    print("4) Fetch restaurant detail page (frontend)")
    r = requests.get(f"{FRONTEND}{rest_path}", timeout=5)
    if r.status_code != 200:
        fail(f"restaurant detail page failed: {r.status_code}")
    print("  ok")

    print("5) Fetch menu via gateway")
    r = requests.get(f"{GATEWAY}/api/v1/restaurantes/{rest_id}/menu", timeout=5)
    if r.status_code != 200:
        fail(f"menu fetch failed: {r.status_code} {r.text}")
    data = r.json()
    # Support both old wrapper {"menu": [...]} and new raw list responses
    if isinstance(data, dict):
        menu = data.get("menu") or data.get("items") or []
    elif isinstance(data, list):
        menu = data
    else:
        menu = []
    if not menu:
        fail("menu is empty")
    item = menu[0]
    # item may be a dict-like object
    item_id = item.get('id') if isinstance(item, dict) else item
    print(f"  menu has {len(menu)} items, picking {item_id}")

    print("6) Create pedido via gateway (authenticated)")
    payload = {
        "restaurante_id": rest_id,
        "cliente_email": email,
        "direccion": "Calle de prueba 1",
        "items": [{"item_id": item.get('id'), "cantidad": 1}],
    }
    r = requests.post(f"{GATEWAY}/api/v1/pedidos/api/v1/pedidos", json=payload, headers=headers, timeout=5)
    if r.status_code not in (200, 201):
        fail(f"create pedido failed: {r.status_code} {r.text}")
    order = r.json()
    order_id = order.get("id")
    if not order_id:
        fail("no order id returned")
    print(f"  created order {order_id}")

    print("7) Fetch the pedido and verify repartidor")
    r = requests.get(f"{GATEWAY}/api/v1/pedidos/api/v1/pedidos/{order_id}", headers=headers, timeout=5)
    if r.status_code != 200:
        fail(f"get pedido failed: {r.status_code} {r.text}")
    data = r.json()
    if not data.get("repartidor"):
        fail("no repartidor assigned in order")
    print("  repartidor assigned:", data.get("repartidor"))

    print("E2E test passed ✅")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        fail(str(e))
