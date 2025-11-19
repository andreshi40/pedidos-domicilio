import time
import requests
import pytest


BASE_GW = "http://localhost:8000/api/v1"
REP_SVC = "http://localhost:8004/api/v1/repartidores"
REST_SVC = "http://localhost:8002/api/v1/restaurantes"


def _find_rest_with_item(min_quantity: int = 1):
    """Busca un restaurante con al menos un item con stock >= min_quantity.
    Retorna (rest, item) o hace skip si no encuentra ninguno.
    """
    try:
        r = requests.get(f"{REST_SVC}?limit=20", timeout=3)
        r.raise_for_status()
    except Exception as e:
        pytest.skip(f"No se pudo conectar a restaurantes service: {e}")

    restos = r.json() or []
    # el endpoint puede devolver dict o lista dependiendo de implementación
    if isinstance(restos, dict) and "restaurantes" in restos:
        restos = restos["restaurantes"]

    for rest in restos:
        try:
            m = requests.get(f"{REST_SVC}/{rest.get('id')}/menu", timeout=3)
            if m.status_code != 200:
                continue
            menu = m.json()
            # menu puede venir en {"menu": [...]} o directamente una lista
            if isinstance(menu, dict) and "menu" in menu:
                items = menu["menu"]
            else:
                items = menu
            for it in items:
                if it.get("cantidad", 0) >= min_quantity:
                    return rest, it
        except Exception:
            continue

    pytest.skip("Ningún restaurante con items disponibles encontrado")


def test_create_order_and_assigns_repartidor():
    # Requisitos: docker-compose arriba con gateway, restaurantes, pedidos y repartidores
    rest, item = _find_rest_with_item(1)

    # Crear un repartidor de prueba (si ya existe, la API debería devoler 201/200 ó 409)
    rep_id = "rt_test_integ"
    rep_payload = {"id": rep_id, "nombre": "Rep Test", "telefono": "3000000001"}
    try:
        requests.post(REP_SVC, json=rep_payload, timeout=3)
    except requests.exceptions.RequestException:
        # no crítico: puede ya existir o el servicio temporalmente inaccesible
        pass

    # Asegurar que el repartidor está libre
    try:
        requests.post(f"{REP_SVC}/{rep_id}/free", timeout=3)
    except Exception:
        pass

    payload = {
        "restaurante_id": rest.get("id"),
        "cliente_email": "test@example.com",
        "direccion": "Calle Test 123",
        "items": [{"item_id": item.get("id"), "cantidad": 1}],
    }

    resp = requests.post(f"{BASE_GW}/pedidos", json=payload, timeout=5)
    assert resp.status_code in (200, 201), (
        f"Expected 200/201 creating order, got {resp.status_code} - {resp.text}"
    )
    data = resp.json()
    order_id = data.get("id")
    assert order_id, "Respuesta no incluyó id de pedido"

    # Esperar a que el pedido sea asignado por el flujo inmediato o por el background assigner
    assigned = False
    for _ in range(12):  # ~12s timeout
        r = requests.get(f"{BASE_GW}/pedidos/{order_id}", timeout=3)
        if r.status_code == 200:
            j = r.json()
            if j.get("estado") == "asignado" and j.get("repartidor"):
                assigned = True
                break
        time.sleep(1)

    assert assigned, f"Pedido {order_id} no fue asignado dentro del timeout"
