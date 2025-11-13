# Resumen de arquitectura y tecnologías

Este documento resume la arquitectura, las tecnologías y las herramientas principales usadas por la aplicación "pedidos-domicilio" y proporciona un diagrama visual (Mermaid) que representa los componentes y sus dependencias.

## Resumen breve
- Arquitectura: microservicios en Python, orquestados por Docker Compose.
- Frontend: Flask (Jinja templates) ejecutando la UI en `http://localhost:5000`.
- API Gateway: FastAPI (forwarding + JWT auth) en `http://localhost:8000`.
- Servicios principales (FastAPI):
  - `restaurantes-service` (Postgres) — puertos internos y endpoints `/api/v1/restaurantes`.
  - `pedidos-service` (Postgres + Redis) — maneja creación de pedidos, reservas y un assigner en background.
  - `repartidores-service` (Postgres) — mantiene repartidores y endpoint `POST /assign-next` para asignación atómica.
  - `authentication` (FastAPI + MongoDB) — login/registro y JWT.
- Bases de datos: Postgres por servicio (`restaurantes-db`, `pedidos-db`, `repartidores-db`), MongoDB para auth, Redis como cache/coordination.
- Comunicaciones: HTTP interno con `requests` entre servicios; gateway centraliza llamadas desde frontend.
- Contenerización: Dockerfiles por servicio y `docker-compose.yml` con volúmenes persistentes.

## Tecnologías (lista rápida)
- Lenguaje: Python
- Frameworks web: FastAPI (APIs), Flask (frontend)
- ASGI server: Uvicorn
- ORM/DB: SQLAlchemy, psycopg2-binary, PostgreSQL
- Otros DB: MongoDB (pymongo), Redis
- HTTP client: requests
- Auth/JWT: python-jose, passlib
- Tooling: Docker, Docker Compose, pytest (tests listadas)

## Diagrama de arquitectura (Mermaid)

Pega el siguiente bloque Mermaid en cualquier visor compatible (GitHub Markdown, mermaid.live o `mmdc`) para renderizarlo como SVG/PNG.

```mermaid
flowchart LR
  subgraph DockerCompose[Docker Compose]
    direction TB
    FE[Frontend\n(Flask :5000)]
    GW[API Gateway\n(FastAPI :8000)]
    subgraph services [Microservicios]
      direction LR
      AUTH[Auth\n(FastAPI :8001)\nMongoDB]
      REST[Restaurantes\n(FastAPI :8002)\nPostgres(restaurantes-db)]
      PED[Pedidos\n(FastAPI :8003)\nPostgres(pedidos-db)\nRedis]
      REP[Repartidores\n(FastAPI :8004)\nPostgres(repartidores-db)]
    end
    subgraph infra [Datastores]
      direction TB
      MONGO[(MongoDB :27017)]
      PG_REST[(Postgres restaur.)]
      PG_PED[(Postgres pedidos)]
      PG_REP[(Postgres repart.)]
      REDIS[(Redis :6379)]
    end
  end

  FE -->|HTTP (browser) | GW
  GW -->|forward /api/v1/auth| AUTH
  GW -->|forward /api/v1/restaurantes| REST
  GW -->|forward /api/v1/pedidos| PED
  GW -->|forward /api/v1/repartidores| REP

  AUTH --> MONGO
  REST --> PG_REST
  PED --> PG_PED
  PED --> REDIS
  REP --> PG_REP

  %% Important flows between services
  PED -->|POST /api/v1/restaurantes/{rid}/menu/{item}/reserve| REST
  PED -->|POST /assign-next| REP
  REP -->|SELECT FOR UPDATE SKIP LOCKED on repartidores| PG_REP

  style DockerCompose fill:#f9f,stroke:#333,stroke-width:1px
  style services fill:#fffbcc,stroke:#333
  style infra fill:#cff,stroke:#333

  %% Notes
  classDef note fill:#eee,stroke:#666,stroke-dasharray: 2 2
  class PED,REP note

```

## Explicación rápida del diagrama
- El `Frontend` se comunica exclusivamente con el `API Gateway` para evitar exponer servicios internos.
- El `API Gateway` enruta peticiones, valida JWT y añade cabeceras de usuario a las llamadas internas.
- `Pedidos` reserva stock en `Restaurantes` y solicita asignación atómica a `Repartidores` usando `POST /assign-next`.
- Cada servicio tiene su propia base de datos PostgreSQL; `authentication` usa MongoDB; `pedidos` usa Redis adicionalmente.

## Cómo renderizar el diagrama a imagen
- Usando mermaid.live: pega el bloque `mermaid` anterior en https://mermaid.live y exporta a PNG/SVG.
- Usando mermaid-cli (local):

```bash
# instalar (requiere nodejs)
npm install -g @mermaid-js/mermaid-cli
# guardar el diagrama en docs/architecture.mmd (o extraer el bloque mermaid del README)
mmdc -i docs/architecture.mmd -o docs/architecture.svg
```

## Archivo alternativo ASCII
Se incluye un fallback ASCII por compatibilidad en `docs/architecture-ascii.txt`.

---
Generado automáticamente por la utilidad de documentación del repo.
