#!/usr/bin/env python3
"""Quick connectivity test for services."""

import requests
import sys

# Test endpoints
tests = [
    ("Gateway health", "http://localhost:8000/health"),
    ("Auth health", "http://localhost:8001/health"),
    ("Restaurantes health", "http://localhost:8002/health"),
    ("Restaurantes list", "http://localhost:8002/api/v1/restaurantes?limit=5"),
    ("Gateway -> Restaurantes", "http://localhost:8000/api/v1/restaurantes?limit=5"),
    ("Pedidos health", "http://localhost:8003/health"),
    ("Repartidores health", "http://localhost:8004/health"),
    ("Frontend", "http://localhost:5000/"),
]

print("=" * 60)
print("SERVICE CONNECTIVITY TEST")
print("=" * 60)

for name, url in tests:
    try:
        resp = requests.get(url, timeout=3)
        status = (
            "✓ OK"
            if resp.status_code in (200, 301, 302)
            else f"✗ HTTP {resp.status_code}"
        )
        print(f"{name:30} {status:15} {url}")
        if "restaurantes" in url.lower() and resp.status_code == 200:
            try:
                data = resp.json()
                if isinstance(data, dict) and "restaurantes" in data:
                    print(f"  -> Found {len(data['restaurantes'])} restaurantes")
                elif isinstance(data, list):
                    print(f"  -> Found {len(data)} items (list format)")
                else:
                    print(
                        f"  -> Response keys: {list(data.keys()) if isinstance(data, dict) else 'N/A'}"
                    )
            except Exception as e:
                print(f"  -> JSON parse error: {e}")
    except requests.exceptions.Timeout:
        print(f"{name:30} ✗ TIMEOUT      {url}")
    except requests.exceptions.ConnectionError:
        print(f"{name:30} ✗ CONN ERR     {url}")
    except Exception as e:
        print(f"{name:30} ✗ ERROR        {url} ({e})")

print("=" * 60)
sys.exit(0)
