from fastapi.testclient import TestClient
import pytest

# Import the FastAPI app and module from the pedidos service
import main as pedidos_main
from main import app

client = TestClient(app)


class DummyResponse:
    def __init__(self, status_code, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data
        self.text = text

    def json(self):
        return self._json


def test_create_pedido_fails_when_item_out_of_stock(monkeypatch):
    # Simulate the restaurantes menu returning item p1 with cantidad 0
    menu = {"menu": [{"id": "p1", "nombre": "Margarita", "precio": 7.5, "cantidad": 0}]}

    def fake_get(url, timeout=2, params=None, headers=None):
        # if the URL ends with /menu return the menu
        if url.endswith("/menu"):
            return DummyResponse(200, json_data=menu)
        # fallback: normal behavior
        return DummyResponse(404, json_data={})

    monkeypatch.setattr(pedidos_main.requests, "get", fake_get)

    payload = {
        "restaurante_id": "rest1",
        "cliente_email": "test@example.com",
        "direccion": "Calle Test 1",
        "items": [{"item_id": "p1", "cantidad": 1}],
    }

    resp = client.post("/api/v1/pedidos", json=payload)
    assert resp.status_code == 400
    body = resp.json()
    assert "sin stock" in body.get("detail", "").lower()


if __name__ == "__main__":
    pytest.main([__file__])
