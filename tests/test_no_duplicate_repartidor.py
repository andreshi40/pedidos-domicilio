import time
import requests
import pytest

BASE_GW = "http://localhost:8000/api/v1"
FRONTEND = "http://localhost:5000"
REP_SVC = "http://localhost:8004/api/v1/repartidores"
REST_SVC = "http://localhost:8002/api/v1/restaurantes"


def _find_rest_with_item(min_quantity: int = 1):
    try:
        r = requests.get(f"{REST_SVC}?limit=20", timeout=3)
        r.raise_for_status()
    except Exception as e:
        pytest.skip(f"No se pudo conectar a restaurantes service: {e}")

    restos = r.json() or []
    if isinstance(restos, dict) and 'restaurantes' in restos:
        restos = restos['restaurantes']

    for rest in restos:
        try:
            m = requests.get(f"{REST_SVC}/{rest.get('id')}/menu", timeout=3)
            if m.status_code != 200:
                continue
            menu = m.json()
            if isinstance(menu, dict) and 'menu' in menu:
                items = menu['menu']
            else:
                items = menu
            for it in items:
                if it.get('cantidad', 0) >= min_quantity:
                    return rest, it
        except Exception:
            continue
    pytest.skip("Ningún restaurante con items disponibles encontrado")


def test_order_page_shows_single_repartidor_block():
    rest, item = _find_rest_with_item(1)

    # ensure a repartidor exists and is free
    rep_id = "rt_test_dup"
    rep_payload = {"id": rep_id, "nombre": "Rep Dup Test", "telefono": "3000000002"}
    try:
        requests.post(REP_SVC, json=rep_payload, timeout=3)
    except Exception:
        pass
    try:
        requests.post(f"{REP_SVC}/{rep_id}/free", timeout=3)
    except Exception:
        pass

    # create order via gateway
    payload = {
        "restaurante_id": rest.get('id'),
        "cliente_email": "dup_test@example.com",
        "direccion": "Calle Dup 1",
        "items": [{"item_id": item.get('id'), "cantidad": 1}]
    }
    resp = requests.post(f"{BASE_GW}/pedidos", json=payload, timeout=5)
    assert resp.status_code in (200,201), f"Crear pedido falló: {resp.status_code} {resp.text}"
    order = resp.json()
    order_id = order.get('id')
    assert order_id

    # wait until assigned
    assigned = False
    for _ in range(15):
        r = requests.get(f"{BASE_GW}/pedidos/{order_id}", timeout=3)
        if r.status_code == 200:
            j = r.json()
            if j.get('estado') == 'asignado' and j.get('repartidor'):
                assigned = True
                rep_name = j['repartidor'].get('nombre')
                break
        time.sleep(1)
    assert assigned, "El pedido no fue asignado en el timeout"

    # fetch the frontend order page HTML
    rhtml = requests.get(f"{FRONTEND}/order/{order_id}", timeout=5)
    assert rhtml.status_code == 200
    html = rhtml.text

    # Count occurrences of the repartidor header and the repartidor name
    header_count = html.count('Repartidor asignado')
    name_count = html.count(rep_name) if rep_name else 0

    assert header_count == 1, f"Se encontraron {header_count} bloques 'Repartidor asignado' en la página (esperado 1)"
    assert name_count == 1, f"Se encontraron {name_count} ocurrencias del nombre del repartidor en la página (esperado 1)"
