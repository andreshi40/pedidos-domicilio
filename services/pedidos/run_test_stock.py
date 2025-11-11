from fastapi.testclient import TestClient

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


def fake_get(url, timeout=2, params=None, headers=None):
    if url.endswith('/menu'):
        return DummyResponse(200, json_data={"menu": [{"id": "p1", "nombre": "Margarita", "precio": 7.5, "cantidad": 0}]})
    return DummyResponse(404, json_data={})

# monkeypatch by assignment
pedidos_main.requests.get = fake_get

payload = {
    "restaurante_id": "rest1",
    "cliente_email": "test@example.com",
    "direccion": "Calle Test 1",
    "items": [{"item_id": "p1", "cantidad": 1}]
}

resp = client.post('/api/v1/pedidos', json=payload)
print('Status code:', resp.status_code)
print('Body:', resp.text)

if resp.status_code == 400 and 'sin stock' in resp.text.lower():
    print('TEST PASSED: pedido rechazado por stock 0')
    exit(0)
else:
    print('TEST FAILED')
    exit(2)
