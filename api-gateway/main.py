from fastapi import FastAPI, APIRouter, Request, HTTPException
from fastapi.responses import JSONResponse
from jose import JWTError, jwt
import os
from fastapi.middleware.cors import CORSMiddleware
import requests

# Define la instancia de la aplicación FastAPI.
app = FastAPI(title="API Gateway Taller Microservicios")

# Configura CORS (Cross-Origin Resource Sharing).
# Esto es esencial para permitir que el frontend se comunique con el gateway.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite peticiones desde cualquier origen (ajustar en producción)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Crea un enrutador para las peticiones de los microservicios.
router = APIRouter(prefix="/api/v1")

# Define los microservicios y sus URLs.
# La URL debe coincidir con el nombre del servicio definido en docker-compose.yml.
# El puerto debe ser el del contenedor (ej. auth-service:8001).
SERVICES = {
    "auth": os.getenv("AUTH_SERVICE_URL", "http://authentication:8001"),
    # Mapea los otros servicios para permitir forwarding desde el gateway.
    "restaurantes": os.getenv("RESTAURANTES_URL", "http://restaurantes-service:8002"),
    "pedidos": os.getenv("PEDIDOS_URL", "http://pedidos-service:8003"),
    "repartidores": os.getenv("REPARTIDORES_URL", "http://repartidores-service:8004"),
}

# JWT settings (will pick from env, use .env via docker-compose)
SECRET_KEY = os.getenv("JWT_SECRET", "change-me-in-production")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


def _is_auth_exempt(service_name: str, path: str) -> bool:
    # allow public auth endpoints
    # First, keep legacy default for auth service (if PUBLIC_ROUTES not set)
    p = path.lstrip("/")
    # Load configured public routes from env (cached per process)
    if not hasattr(_is_auth_exempt, "_public_patterns"):
        raw = os.getenv("PUBLIC_ROUTES", "auth:login,auth:register,auth:health")
        patterns = []
        for part in [p.strip() for p in raw.split(",") if p.strip()]:
            # expected format service:route or service:route*
            if ":" not in part:
                continue
            svc, rp = part.split(":", 1)
            patterns.append((svc, rp))
        _is_auth_exempt._public_patterns = patterns

    for svc, rp in _is_auth_exempt._public_patterns:
        if svc != service_name:
            continue
        # exact match or wildcard suffix
        if rp.endswith("*"):
            prefix = rp[:-1].lstrip("/")
            if p.startswith(prefix):
                return True
        else:
            if p == rp.lstrip("/") or p.startswith(rp.lstrip("/")) and rp == "":
                return True
    return False


def _verify_token_from_request(request: Request):
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    token = auth.split(None, 1)[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    # extract commonly used claims
    return {"sub": payload.get("sub"), "email": payload.get("email"), "role": payload.get("role")}

# TODO: Implementa una ruta genérica para redirigir peticiones GET.
@router.get("/{service_name}/{path:path}")
async def forward_get(service_name: str, path: str, request: Request):
    if service_name not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found.")
    service_url = f"{SERVICES[service_name]}/{path}"

    # Validate token unless endpoint is exempt (e.g. auth/login, auth/register, auth/health)
    headers = {k: v for k, v in request.headers.items()}
    if not _is_auth_exempt(service_name, path):
        user = _verify_token_from_request(request)
        # add user headers for downstream services
        headers["X-User-Id"] = str(user.get("sub"))
        if user.get("email"):
            headers["X-User-Email"] = str(user.get("email"))
        if user.get("role"):
            headers["X-User-Role"] = str(user.get("role"))

    try:
        response = requests.get(service_url, params=request.query_params, headers=headers)
        # Forward the downstream status code and body transparently.
        try:
            return JSONResponse(status_code=response.status_code, content=response.json())
        except ValueError:
            return JSONResponse(status_code=response.status_code, content={"detail": response.text})
    except requests.exceptions.RequestException as e:
        # Network/connection errors should still map to 500 from the gateway.
        raise HTTPException(status_code=500, detail=f"Error forwarding request to {service_name}: {e}")

# TODO: Implementa una ruta genérica para redirigir peticiones POST.
@router.post("/{service_name}/{path:path}")
async def forward_post(service_name: str, path: str, request: Request):
    if service_name not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found.")
    service_url = f"{SERVICES[service_name]}/{path}"

    headers = {k: v for k, v in request.headers.items()}
    if not _is_auth_exempt(service_name, path):
        user = _verify_token_from_request(request)
        headers["X-User-Id"] = str(user.get("sub"))
        if user.get("email"):
            headers["X-User-Email"] = str(user.get("email"))
        if user.get("role"):
            headers["X-User-Role"] = str(user.get("role"))

    try:
        # Pasa los datos JSON del cuerpo de la petición.
        body = None
        try:
            body = await request.json()
        except Exception:
            body = None
        response = requests.post(service_url, json=body, headers=headers)
        # Forward downstream status and body transparently.
        try:
            return JSONResponse(status_code=response.status_code, content=response.json())
        except ValueError:
            return JSONResponse(status_code=response.status_code, content={"detail": response.text})
    except requests.exceptions.RequestException as e:
        raise HTTPException(status_code=500, detail=f"Error forwarding request to {service_name}: {e}")

# TODO: Agrega más rutas para otros métodos HTTP (PUT, DELETE, etc.).

# Incluye el router en la aplicación principal.
app.include_router(router)

# Endpoint de salud para verificar el estado del gateway.
@app.get("/health")
def health_check():
    return {"status": "ok", "message": "API Gateway is running."}
