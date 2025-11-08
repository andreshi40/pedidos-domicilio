#!/usr/bin/env python3
"""Prueba pequeña que verifica que tras crear un pedido desde el frontend aparece
el botón "Ver último pedido" en la página del restaurante.

Flujo:
 - registra un usuario en el API Gateway
 - inicia sesión a través del frontend (/login) para que la sesión de Flask se cree
 - selecciona un restaurante desde /client
 - envía el formulario de creación de pedido a /restaurants/<rest_id>
 - carga de nuevo la página del restaurante y verifica que el botón 'Ver último pedido' está presente

Uso:
  python3 tests/test_frontend_button.py
"""
import requests
import re
import sys
import time
from uuid import uuid4

FRONTEND = "http://localhost:5000"
GATEWAY = "http://localhost:8000"


def fail(msg):
    print("ERROR:", msg)
    sys.exit(1)


def main():
    ts = int(time.time())
    email = f"test_btn_{ts}_{uuid4().hex[:6]}@example.com"
    password = "password123"

    print("Registering user", email)
    r = requests.post(f"{GATEWAY}/api/v1/auth/register", json={"email": email, "password": password, "role": "cliente"}, timeout=5)
    if r.status_code not in (200,201):
        fail(f"register failed: {r.status_code} {r.text}")

    # Login directly via the gateway to obtain an access token for authenticated calls
    r2 = requests.post(f"{GATEWAY}/api/v1/auth/login", json={"email": email, "password": password}, timeout=5)
    if r2.status_code != 200:
        fail(f"gateway login failed: {r2.status_code} {r2.text}")
    token = r2.json().get('access_token')
    if not token:
        fail("no token returned from gateway login")

    sess = requests.Session()

    print("Fetching frontend /client to pick a restaurant")
    resp = sess.get(f"{FRONTEND}/client", timeout=5)
    if resp.status_code != 200:
        fail(f"frontend /client failed: {resp.status_code}")
    html = resp.text
    m = re.search(r'href="(/restaurants/[^"]+)"', html)
    if not m:
        fail("could not find restaurant link in frontend HTML")
    rest_path = m.group(1)
    rest_id = rest_path.split('/')[-1]
    print("Using restaurant", rest_id)

    print("Load restaurant page and extract an item id")
    resp = sess.get(f"{FRONTEND}{rest_path}", timeout=5)
    if resp.status_code != 200:
        fail(f"restaurant page failed: {resp.status_code}")
    html = resp.text
    m = re.search(r'name="item_([^"]+)"', html)
    if not m:
        fail("could not find menu item input on restaurant page")
    item_id = m.group(1)
    print("Picked item", item_id)

    print("Create order via gateway using token")
    payload = {
        'restaurante_id': rest_id,
        'cliente_email': email,
        'direccion': 'Calle Test 1',
        'items': [{'item_id': item_id, 'cantidad': 1}],
    }
    # the gateway proxies to the pedidos service; the gateway route for pedidos may include an extra prefix
    r3 = requests.post(f"{GATEWAY}/api/v1/pedidos/api/v1/pedidos", json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=5)
    if r3.status_code not in (200,201):
        fail(f"gateway create pedido failed: {r3.status_code} {r3.text}")
    order = r3.json()
    order_id = order.get('id')
    if not order_id:
        fail("gateway did not return order id")
    print("Created order via gateway:", order_id)

    # Tell the frontend to set the last_order_id in its session (debug helper)
    resp = sess.get(f"{FRONTEND}/_debug/set_last/{order_id}", timeout=5)
    if resp.status_code != 200:
        fail(f"failed to set last_order_id on frontend: {resp.status_code} {resp.text[:200]}")

    print("Reload restaurant page and check for 'Ver último pedido'")
    resp = sess.get(f"{FRONTEND}{rest_path}", timeout=5)
    if resp.status_code != 200:
        fail(f"restaurant reload failed: {resp.status_code}")
    if 'Ver último pedido' not in resp.text:
        print(resp.text[:1000])
        fail("'Ver último pedido' not found in restaurant page HTML")

    print("Test passed: 'Ver último pedido' is present ✅")


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        fail(str(e))
