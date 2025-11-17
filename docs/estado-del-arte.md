# Estado del Arte aplicado al proyecto "Pedidos a Domicilio"

Este análisis no enumera tecnologías; construye una narrativa que explica cómo las decisiones del proyecto responden a los desafíos actuales: velocidad, resiliencia, escalabilidad y mantenibilidad. Se enfatizan las transiciones clave del estado del arte: de WSGI a ASGI, del monolito al microservicio, de procesos manuales a CI/CD, y de documentación estática a documentación viva.

---

## 1. Desarrollo de APIs y Backend — De WSGI a ASGI con FastAPI

- Tendencia: la adopción de ASGI habilita IO asíncrono, mejor throughput y menor latencia frente a WSGI. FastAPI capitaliza ASGI, tipado estático y OpenAPI.
- Adopción en el proyecto:
  - Servicios `restaurantes`, `pedidos`, `repartidores` y `authentication` implementados con FastAPI (auto-docs: `/docs` vía OpenAPI/Swagger).
  - Validación con Pydantic y tipado explícito → menor superficie de errores y DX superior.
- Brecha y plan incremental:
  - Actualmente las llamadas entre servicios usan `requests` (sincrónico). Para rutas críticas (p. ej., creación de pedidos y asignación de repartidores), migrar a `httpx` async + `async def` en endpoints que sólo hacen IO.
  - Adoptar un servidor ASGI performante (uvicorn/uvloop) ya soportado en Dockerfiles; validar `--workers` y `--loop uvloop` en producción.
- Por qué es estado del arte:
  - APIs auto-documentadas por diseño (OpenAPI), tipadas y preparadas para IO asíncrono; benchmarks independientes sitúan FastAPI entre los frameworks Python de mayor rendimiento para APIs.

---

## 2. Arquitectura y Despliegue — Del monolito a Microservicios contenerizados

- Tendencia: descomposición en microservicios, empaquetados con Docker y orquestados (Compose/Kubernetes). Un API Gateway centraliza enrutamiento y políticas.
- Adopción en el proyecto:
  - Microservicios independientes (codebases separadas), cada uno con su base de datos dedicada: Postgres por servicio, MongoDB para Auth, Redis para coordinación de `pedidos`.
  - `docker-compose.yml` define red interna, puertos, volúmenes persistentes (fotos de restaurantes), y dependencias de arranque.
  - API Gateway (FastAPI) enruta `/api/v1/*`, inyecta cabeceras de identidad y maneja CORS/JWT.
- Justificación técnica:
  - Aislamiento de fallos: caída de `repartidores` no afecta autenticación.
  - Escalado dirigido: `pedidos` puede escalarse horizontalmente con Redis y DB propios.
- Plan de madurez:
  - Añadir circuit breakers y timeouts sistemáticos (ya hay timeouts) + retires idempotentes para llamadas internas.
  - Evaluar transición de Compose → Kubernetes si se requiere autoescalado/observabilidad avanzada.

---

## 3. Frontend y UX — UI desacoplada sobre APIs REST

- Tendencia: separación estricta UI/API. El frontend consume APIs y no accede a datos internos.
- Adopción en el proyecto:
  - Frontend (Flask + Jinja) consume exclusivamente el API Gateway y, cuando es necesario por eficiencia, servicios internos para endpoints no expuestos.
  - Seguimiento de pedidos con polling y actualización del DOM (estado "En camino" → "Pedido entregado").
- Plan incremental:
  - Introducir WebSockets o Server-Sent Events para eventos de estado de pedido en tiempo real, reduciendo polling.
  - Estabilizar contrato API con esquemas compartidos (pydantic models publicados).

---

## 4. Calidad con Pruebas Automatizadas — Pirámide de Pruebas con Pytest

- Modelo predominante: Pirámide de Pruebas
  - Base (Unitarias): Pytest por sintaxis clara, fixtures y ecosistema (coverage, pytest-asyncio)
  - Centro (Integración): servicios + DB real (Postgres en contenedor), validando operaciones con SQLAlchemy
  - Pico (End-to-End): flujos usuario → pedido → asignación → entrega con Compose levantado
- Adopción y plan:
  - Hoy no hay suite formal versionada; se propone:
    1) Tests unitarios por servicio (modelos/validaciones/lógica de estado).
    2) Tests de integración contra DB usando fixtures que arrancan contenedores efímeros (testcontainers-py) o servicios de Compose en profile `test`.
    3) Smoke E2E con `docker compose up -d` + scripts que simulan un flujo real.
  - Métricas: coverage mínimo 70% en dominios críticos (`pedidos`, `repartidores`).

---

## 5. Operaciones y DevOps (CI/CD) — Automatización del ciclo de vida

- Prácticas recomendadas:
  - Pre-commit hooks: formato (black), linting (ruff), typing (mypy), seguridad (bandit), y orden de imports (isort) antes de aceptar commits.
  - CI/CD con GitHub Actions: jobs para lint/test/build; optionally publicar imágenes Docker.
- Adopción propuesta:
  - `.pre-commit-config.yaml` con black, ruff, isort, bandit, trailing-whitespace.
  - `ci.yml` en `.github/workflows/` que ejecute: `pip install -r requirements.txt` por servicio, `pytest`, y build de imágenes en pushes a `main`.
  - Estrategia de ramas: `feature/*`, `fix/*`, `chore/*` (ya documentado en `INCREMENTAL.md`).

---

## 6. Persistencia de Datos — SQLAlchemy como toolkit (Data Mapper)

- Tendencia: ORMs maduros con separación de dominio/infraestructura.
- Adopción en el proyecto:
  - SQLAlchemy ORM en `restaurantes`, `pedidos`, `repartidores` con esquemas explícitos y relaciones; transacciones y bloqueos (`SELECT FOR UPDATE`) para consistencia.
  - Redis en `pedidos` como cache/coordination (preparado) para flujos de asignación.
- Comparativa:
  - Data Mapper (SQLAlchemy) vs Active Record: mayor expresividad y control transaccional; Core permite consultas complejas y portabilidad.
- Plan incremental:
  - Añadir índices y constraints a nivel ORM/migraciones (Alembic) para evolución segura del esquema.

---

## 7. Documentación — Documentación como código (Docs-as-Code)

- Tendencia: documentación en Markdown, versionada, navegable y desplegable con CI.
- Adopción actual:
  - Documentos en `docs/` (arquitectura, caso de uso, incremental, etapas incrementales).
- Plan para estado del arte completo:
  - Introducir MkDocs o Docusaurus con tema material, navegación por secciones (Arquitectura, APIs, Operación, Casos de uso).
  - Publicación automática en GitHub Pages desde `main`.

---

## 8. Transiciones clave y cómo se materializan en el proyecto

- Síncrono → Asíncrono: migración selectiva a `async`/`httpx` en rutas de alto tráfico (crear pedido, asignar repartidor). Beneficio: mejor utilización del loop IO y reducción de latencia bajo carga.
- Monolito → Microservicios: separación por contexto (restaurantes/pedidos/repartidores/auth), bases de datos per-service y comunicación vía HTTP; facilita escalar equipos y despliegues.
- Manual → CI/CD: del build manual a pipelines que validan, testean y publican imágenes; calidad verificable en cada push.
- Documentación estática → Viva: docs versionadas, generadas y publicadas en cada release (MkDocs + Actions).

---

## 9. Evidencias en el repositorio

- `docker-compose.yml`: servicios, bases de datos, volúmenes persistentes y red interna.
- `services/*/main.py`: FastAPI, Pydantic, endpoints con validaciones. `pedidos` con liberación automática de repartidor y estadísticas.
- `frontend/`: UI que consume APIs, estados dinámicos de pedido y branding consistente (SVG).
- `docs/`: arquitectura, caso de uso, flujo incremental, etapas.

---

## 10. Roadmap mínimo para alcanzar el “estado del arte” completo

1) Migración IO crítico a async (`httpx`, `async def`, uvicorn/uvloop).  
2) Pre-commit + CI (lint, tests, build).  
3) Suite Pytest (unit/integration/E2E) con coverage.  
4) MkDocs + GitHub Pages (docs vivas).  
5) Observabilidad: logs estructurados, métricas (Prometheus) y tracing (OTel) en `pedidos`.

---

## Conclusión

El proyecto no es un conjunto arbitrario de componentes: es una aplicación consciente de las tendencias actuales. FastAPI y ASGI aportan velocidad y DX; la arquitectura de microservicios con Docker ofrece resiliencia y escalabilidad; SQLAlchemy garantiza mantenibilidad del dominio; y la hoja de ruta hacia CI/CD, pruebas y documentación viva completa el cuadro de un sistema moderno, sostenible y alineado con el estado del arte de la industria.
