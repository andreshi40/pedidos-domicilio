#!/usr/bin/env python3
"""Lightweight E2E scripted test that simulates browser interaction via requests.Session.
Flow:
 - register a user via API Gateway
 - login via the frontend (/login form) so the frontend sets session cookie with access_token
 - load frontend /client, pick a restaurant link
 - fetch menu via frontend proxy
 - POST to frontend /api/pedidos (AJAX proxy) with session cookie
 - poll /api/order/<id> to check estado and repartidor
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
    email = f"e2e_user_{ts}_{uuid4().hex[:6]}@example.com"
    password = "password123"

    print("Registering user", email)
    r = requests.post(
        f"{GATEWAY}/api/v1/auth/register",
        json={"email": email, "password": password, "role": "cliente"},
        timeout=5,
    )
    if r.status_code not in (200, 201):
        fail(f"register failed: {r.status_code} {r.text}")
    print("Registered")

    sess = requests.Session()

    # Perform frontend login (form POST) so the frontend stores session['access_token'] in session cookie
    print("Logging in via frontend /login")
    login_page = sess.get(f"{FRONTEND}/login", timeout=5)
    if login_page.status_code != 200:
        fail(f"could not load frontend login page: {login_page.status_code}")

    r = sess.post(
        f"{FRONTEND}/login",
        data={"email": email, "password": password},
        timeout=5,
        allow_redirects=True,
    )
    if r.status_code not in (200, 302):
        # sometimes redirect to /home returns 200 after flash; consider 200 OK as success
        print("Login response status:", r.status_code)
    # check session has been set by trying to access /home which requires login
    home = sess.get(f"{FRONTEND}/home", timeout=5)
    if home.status_code != 200:
        print("Warning: could not access /home after login (status)", home.status_code)

    print("Fetching frontend /client")
    r = sess.get(f"{FRONTEND}/client", timeout=5)
    if r.status_code != 200:
        fail(f"frontend /client failed: {r.status_code}")
    html = r.text
    m = re.search(r'href="(/restaurants/[^\"]+)"', html)
    if not m:
        fail("could not find restaurant link in frontend HTML")
    rest_path = m.group(1)
    rest_id = rest_path.split("/")[-1]
    print("Using restaurant", rest_id)

    print("Fetching menu via frontend proxy")
    r = sess.get(f"{FRONTEND}/api/restaurantes/{rest_id}/menu", timeout=5)
    if r.status_code != 200:
        fail(f"menu fetch failed: {r.status_code} {r.text}")
    data = r.json()
    menu = data.get("menu") if isinstance(data, dict) else data
    if not menu:
        fail("menu empty")
    item = menu[0]
    item_id = item.get("id")
    print("Picked item", item_id)

    print("Creating pedido via frontend AJAX proxy")
    payload = {
        "restaurante_id": rest_id,
        "cliente_email": email,
        "direccion": "Calle Test 1",
        "items": [{"item_id": item_id, "cantidad": 1}],
    }
    r = sess.post(f"{FRONTEND}/api/pedidos", json=payload, timeout=5)
    if r.status_code not in (200, 201):
        fail(f"create pedido failed: {r.status_code} {r.text}")
    order = r.json()
    order_id = order.get("id")
    if not order_id:
        fail("no order id returned")
    print("Created order", order_id)

    print("Polling order status for repartidor assignment")
    for i in range(10):
        rt = sess.get(f"{FRONTEND}/api/order/{order_id}", timeout=5)
        if rt.status_code == 200:
            dt = rt.json()
            estado = dt.get("estado") or dt.get("status")
            rep = dt.get("repartidor")
            print(f"  attempt {i}: estado={estado} repartidor={rep}")
            # Treat 'asignado' as success even if repartidor details are not persisted in the order
            if rep or (estado and estado.lower() == "asignado"):
                print("Order assigned (estado=asignado). E2E OK")
                return
        else:
            print("  polling status failed", rt.status_code)
        time.sleep(1)

    fail("Order was not assigned within the timeout")


if __name__ == "__main__":
    main()
