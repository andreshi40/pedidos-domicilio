# Diagrama de Orquestación Docker - Pedidos a Domicilio

## Arquitectura de Contenedores

```mermaid
graph TB
    subgraph "Usuario/Cliente"
        USER[👤 Usuario<br/>Browser]
    end

    subgraph "Docker Network"
        subgraph "Frontend Layer"
            FRONT[🌐 Frontend<br/>Flask App<br/>:5000]
        end

        subgraph "Gateway Layer"
            GW[🚪 API Gateway<br/>FastAPI<br/>:8000]
        end

        subgraph "Microservices Layer"
            AUTH[🔐 Authentication<br/>FastAPI<br/>:8001]
            REST[🍕 Restaurantes<br/>FastAPI<br/>:8002]
            PED[📦 Pedidos<br/>FastAPI<br/>:8003]
            REP[🚴 Repartidores<br/>FastAPI<br/>:8004]
        end

        subgraph "Database Layer"
            MONGO[(MongoDB<br/>auth-db<br/>:27017)]
            PG1[(PostgreSQL<br/>restaurantes-db<br/>:5432)]
            PG2[(PostgreSQL<br/>pedidos-db<br/>:5433)]
            PG3[(PostgreSQL<br/>repartidores-db<br/>:5435)]
            REDIS[(Redis<br/>:6379)]
        end

        subgraph "Storage Layer"
            VOL1[📁 auth_data]
            VOL2[📁 restaurantes_data]
            VOL3[📁 pedidos_data]
            VOL4[📁 repartidores_data]
            VOL5[📁 redis_data]
            VOL6[📁 restaurante_photos]
        end
    end

    USER -->|HTTP :5000| FRONT
    FRONT -->|HTTP :8000| GW
    GW -->|JWT Validation| AUTH
    GW -->|Forward Requests| REST
    GW -->|Forward Requests| PED
    GW -->|Forward Requests| REP

    AUTH -->|Read/Write| MONGO
    AUTH -->|Store Tokens| REDIS
    REST -->|CRUD| PG1
    REST -->|Save Photos| VOL6
    PED -->|CRUD| PG2
    PED -->|Coordination| REDIS
    REP -->|CRUD| PG3

    MONGO -.->|Persist| VOL1
    PG1 -.->|Persist| VOL2
    PG2 -.->|Persist| VOL3
    PG3 -.->|Persist| VOL4
    REDIS -.->|Persist| VOL5

    style USER fill:#e1f5ff
    style FRONT fill:#4caf50
    style GW fill:#ff9800
    style AUTH fill:#2196f3
    style REST fill:#9c27b0
    style PED fill:#f44336
    style REP fill:#00bcd4
    style MONGO fill:#4db33d
    style PG1 fill:#336791
    style PG2 fill:#336791
    style PG3 fill:#336791
    style REDIS fill:#dc382d
```

## Diagrama de Dependencias entre Contenedores

```mermaid
graph LR
    FRONT[frontend] -->|depends_on| GW[api-gateway]
    GW -->|depends_on| AUTH[authentication]

    AUTH -->|depends_on| AUTHDB[(auth-db)]

    REST[restaurantes-service] -->|depends_on| RESTDB[(restaurantes-db)]

    PED[pedidos-service] -->|depends_on| PEDDB[(pedidos-db)]
    PED -->|depends_on| REDIS[(redis)]

    REP[repartidores-service] -->|depends_on| REPDB[(repartidores-db)]

    style FRONT fill:#4caf50
    style GW fill:#ff9800
    style AUTH fill:#2196f3
    style REST fill:#9c27b0
    style PED fill:#f44336
    style REP fill:#00bcd4
    style AUTHDB fill:#4db33d
    style RESTDB fill:#336791
    style PEDDB fill:#336791
    style REPDB fill:#336791
    style REDIS fill:#dc382d
```

## Diagrama de Red Docker

```mermaid
graph TB
    subgraph "Host Machine"
        P5000["Port 5000<br/>(Frontend)"]
        P8000["Port 8000<br/>(Gateway)"]
        P8001["Port 8001<br/>(Auth)"]
        P8002["Port 8002<br/>(Restaurantes)"]
        P8003["Port 8003<br/>(Pedidos)"]
        P8004["Port 8004<br/>(Repartidores)"]
        P27017["Port 27017<br/>(MongoDB)"]
        P5432["Port 5432<br/>(Restaurantes DB)"]
        P5433["Port 5433<br/>(Pedidos DB)"]
        P5435["Port 5435<br/>(Repartidores DB)"]
        P6379["Port 6379<br/>(Redis)"]
    end

    subgraph "Docker Bridge Network (default)"
        FRONT[frontend:5000]
        GW[api-gateway:8000]
        AUTH[authentication:8001]
        REST[restaurantes-service:8002]
        PED[pedidos-service:8003]
        REP[repartidores-service:8004]
        MONGO[auth-db:27017]
        PG1[restaurantes-db:5432]
        PG2[pedidos-db:5432]
        PG3[repartidores-db:5432]
        REDIS[redis:6379]
    end

    P5000 -.->|Expose| FRONT
    P8000 -.->|Expose| GW
    P8001 -.->|Expose| AUTH
    P8002 -.->|Expose| REST
    P8003 -.->|Expose| PED
    P8004 -.->|Expose| REP
    P27017 -.->|Expose| MONGO
    P5432 -.->|Expose| PG1
    P5433 -.->|Expose| PG2
    P5435 -.->|Expose| PG3
    P6379 -.->|Expose| REDIS

    FRONT -.->|Internal DNS| GW
    GW -.->|Internal DNS| AUTH
    GW -.->|Internal DNS| REST
    GW -.->|Internal DNS| PED
    GW -.->|Internal DNS| REP
    AUTH -.->|Internal DNS| MONGO
    AUTH -.->|Internal DNS| REDIS
    REST -.->|Internal DNS| PG1
    PED -.->|Internal DNS| PG2
    PED -.->|Internal DNS| REDIS
    REP -.->|Internal DNS| PG3

    style FRONT fill:#4caf50
    style GW fill:#ff9800
    style AUTH fill:#2196f3
    style REST fill:#9c27b0
    style PED fill:#f44336
    style REP fill:#00bcd4
```

## Diagrama de Volúmenes Docker

```mermaid
graph LR
    subgraph "Docker Volumes"
        V1[auth_data]
        V2[restaurantes_data]
        V3[pedidos_data]
        V4[repartidores_data]
        V5[redis_data]
        V6[restaurante_photos]
    end

    subgraph "Containers"
        MONGO[auth-db]
        PG1[restaurantes-db]
        PG2[pedidos-db]
        PG3[repartidores-db]
        REDIS[redis]
        REST[restaurantes-service]
    end

    MONGO -->|/data/db| V1
    PG1 -->|/var/lib/postgresql| V2
    PG2 -->|/var/lib/postgresql| V3
    PG3 -->|/var/lib/postgresql| V4
    REDIS -->|/data| V5
    REST -->|/app/data/restaurante_photos| V6

    style V1 fill:#ffeb3b
    style V2 fill:#ffeb3b
    style V3 fill:#ffeb3b
    style V4 fill:#ffeb3b
    style V5 fill:#ffeb3b
    style V6 fill:#ffeb3b
    style MONGO fill:#4db33d
    style PG1 fill:#336791
    style PG2 fill:#336791
    style PG3 fill:#336791
    style REDIS fill:#dc382d
    style REST fill:#9c27b0
```

## Secuencia de Inicio de Contenedores

```mermaid
sequenceDiagram
    participant DC as docker-compose
    participant DB as Databases
    participant MS as Microservices
    participant GW as API Gateway
    participant FE as Frontend

    DC->>DB: 1. Iniciar bases de datos
    Note over DB: auth-db (MongoDB)<br/>restaurantes-db (PostgreSQL)<br/>pedidos-db (PostgreSQL)<br/>repartidores-db (PostgreSQL)<br/>redis

    DB-->>DC: Databases ready

    DC->>MS: 2. Iniciar microservicios
    Note over MS: authentication:8001<br/>restaurantes-service:8002<br/>pedidos-service:8003<br/>repartidores-service:8004

    MS->>DB: Conectar a DBs
    MS-->>DC: Services ready

    DC->>GW: 3. Iniciar API Gateway
    GW->>MS: Verificar disponibilidad
    GW-->>DC: Gateway ready

    DC->>FE: 4. Iniciar Frontend
    FE->>GW: Verificar conexión
    FE-->>DC: Frontend ready

    Note over DC,FE: Aplicación completamente iniciada
```

## Flujo de Comunicación entre Contenedores

```mermaid
flowchart LR
    USER[👤 Usuario]

    subgraph "Docker Network"
        FRONT[Frontend<br/>Container]
        GW[Gateway<br/>Container]
        AUTH[Auth<br/>Container]
        REST[Restaurantes<br/>Container]
        PED[Pedidos<br/>Container]
        REP[Repartidores<br/>Container]

        MONGO[(MongoDB)]
        PG1[(PostgreSQL)]
        PG2[(PostgreSQL)]
        PG3[(PostgreSQL)]
        REDIS[(Redis)]
    end

    USER -->|1. HTTP Request<br/>localhost:5000| FRONT
    FRONT -->|2. API Call<br/>api-gateway:8000| GW

    GW -->|3a. Validate JWT<br/>authentication:8001| AUTH
    GW -->|3b. Forward<br/>restaurantes-service:8002| REST
    GW -->|3c. Forward<br/>pedidos-service:8003| PED
    GW -->|3d. Forward<br/>repartidores-service:8004| REP

    AUTH <-->|Query/Save| MONGO
    AUTH <-->|Token Storage| REDIS
    REST <-->|Query/Save| PG1
    PED <-->|Query/Save| PG2
    PED <-->|Lock/Coordination| REDIS
    REP <-->|Query/Save| PG3

    style USER fill:#e1f5ff
    style FRONT fill:#4caf50
    style GW fill:#ff9800
    style AUTH fill:#2196f3
    style REST fill:#9c27b0
    style PED fill:#f44336
    style REP fill:#00bcd4
```

## Tabla de Contenedores y Configuración

| Contenedor | Imagen Base | Puerto Host | Puerto Container | Volumen | Variables de Entorno |
|------------|-------------|-------------|------------------|---------|----------------------|
| **frontend** | Python 3.12 (custom) | 5000 | 5000 | - | `API_GATEWAY_URL=http://api-gateway:8000`<br/>`FLASK_SECRET` |
| **api-gateway** | Python 3.12 (custom) | 8000 | 8000 | - | `JWT_SECRET`<br/>`PUBLIC_ROUTES` |
| **authentication** | Python 3.12 (custom) | 8001 | 8001 | - | `DATABASE_URL=mongodb://auth-db:27017/auth_db`<br/>`JWT_SECRET` |
| **restaurantes-service** | Python 3.12 (custom) | 8002 | 8002 | `restaurante_photos` | `DATABASE_URL=postgresql://user:password@restaurantes-db:5432/service1_db` |
| **pedidos-service** | Python 3.12 (custom) | 8003 | 8003 | - | `DATABASE_URL=postgresql://user:password@pedidos-db:5432/pedidos_db`<br/>`REDIS_URL=redis://redis:6379/0` |
| **repartidores-service** | Python 3.12 (custom) | 8004 | 8004 | - | `DATABASE_URL=postgresql://user:password@repartidores-db:5432/repartidores_db` |
| **auth-db** | mongo:latest | 27017 | 27017 | `auth_data` | - |
| **restaurantes-db** | postgres:latest | 5432 | 5432 | `restaurantes_data` | `POSTGRES_USER=user`<br/>`POSTGRES_PASSWORD=password`<br/>`POSTGRES_DB=service1_db` |
| **pedidos-db** | postgres:latest | 5433 | 5432 | `pedidos_data` | `POSTGRES_USER=user`<br/>`POSTGRES_PASSWORD=password`<br/>`POSTGRES_DB=pedidos_db` |
| **repartidores-db** | postgres:latest | 5435 | 5432 | `repartidores_data` | `POSTGRES_USER=user`<br/>`POSTGRES_PASSWORD=password`<br/>`POSTGRES_DB=repartidores_db` |
| **redis** | redis:alpine | 6379 | 6379 | `redis_data` | - |

## Comandos Docker Compose

### Iniciar todos los contenedores
```bash
docker-compose up -d
```

### Ver logs de todos los servicios
```bash
docker-compose logs -f
```

### Ver logs de un servicio específico
```bash
docker-compose logs -f frontend
docker-compose logs -f api-gateway
docker-compose logs -f authentication
```

### Detener todos los contenedores
```bash
docker-compose down
```

### Detener y eliminar volúmenes
```bash
docker-compose down -v
```

### Reconstruir contenedores
```bash
docker-compose build
docker-compose up -d --build
```

### Escalar un servicio (ejemplo: 3 instancias de pedidos)
```bash
docker-compose up -d --scale pedidos-service=3
```

### Verificar estado de contenedores
```bash
docker-compose ps
```

### Entrar a un contenedor
```bash
docker-compose exec frontend bash
docker-compose exec authentication bash
```

## Ventajas de la Orquestación con Docker

```mermaid
mindmap
  root((Docker<br/>Compose))
    Aislamiento
      Cada servicio en su contenedor
      Dependencias encapsuladas
      Sin conflictos de puertos
    Escalabilidad
      Fácil replicación de servicios
      Balanceo de carga
      Alta disponibilidad
    Portabilidad
      Mismo entorno en dev/prod
      Reproducibilidad garantizada
      Compatible multi-plataforma
    Desarrollo
      Inicio rápido con un comando
      Logs centralizados
      Debugging simplificado
    Persistencia
      Volúmenes para datos
      Backups automáticos
      Estado preservado
    Red Interna
      DNS automático
      Comunicación segura
      Aislamiento de red
```

## Arquitectura de Capas

```mermaid
graph TB
    subgraph "Layer 1: Presentation"
        L1[Frontend Container<br/>Flask App<br/>Templates + Static]
    end

    subgraph "Layer 2: API Gateway"
        L2[API Gateway Container<br/>FastAPI<br/>JWT Validation + Routing]
    end

    subgraph "Layer 3: Business Logic"
        L3A[Authentication<br/>Service]
        L3B[Restaurantes<br/>Service]
        L3C[Pedidos<br/>Service]
        L3D[Repartidores<br/>Service]
    end

    subgraph "Layer 4: Data Access"
        L4A[(MongoDB)]
        L4B[(PostgreSQL)]
        L4C[(PostgreSQL)]
        L4D[(PostgreSQL)]
        L4E[(Redis)]
    end

    subgraph "Layer 5: Persistence"
        L5A[auth_data volume]
        L5B[restaurantes_data volume]
        L5C[pedidos_data volume]
        L5D[repartidores_data volume]
        L5E[redis_data volume]
        L5F[photos volume]
    end

    L1 --> L2
    L2 --> L3A
    L2 --> L3B
    L2 --> L3C
    L2 --> L3D

    L3A --> L4A
    L3A --> L4E
    L3B --> L4B
    L3C --> L4C
    L3C --> L4E
    L3D --> L4D

    L4A -.-> L5A
    L4B -.-> L5B
    L4C -.-> L5C
    L4D -.-> L5D
    L4E -.-> L5E
    L3B -.-> L5F

    style L1 fill:#4caf50
    style L2 fill:#ff9800
    style L3A fill:#2196f3
    style L3B fill:#9c27b0
    style L3C fill:#f44336
    style L3D fill:#00bcd4
```

## Diagrama de Health Checks

```mermaid
sequenceDiagram
    participant U as Usuario
    participant F as Frontend
    participant G as Gateway
    participant A as Auth
    participant R as Restaurantes
    participant P as Pedidos
    participant D as Repartidores

    U->>F: GET /
    F->>G: GET /api/v1/auth/health
    G->>A: Forward health check
    A-->>G: {"status": "ok"}
    G-->>F: 200 OK

    F->>G: GET /api/v1/restaurantes/health
    G->>R: Forward health check
    R-->>G: {"status": "ok"}
    G-->>F: 200 OK

    F->>G: GET /api/v1/pedidos/health
    G->>P: Forward health check
    P-->>G: {"status": "ok"}
    G-->>F: 200 OK

    F->>G: GET /api/v1/repartidores/health
    G->>D: Forward health check
    D-->>G: {"status": "ok"}
    G-->>F: 200 OK

    F-->>U: Dashboard con estado de servicios
```

## Resumen de la Orquestación

La aplicación **Pedidos a Domicilio** utiliza **Docker Compose** para orquestar 11 contenedores:

**Servicios de Aplicación (6):**
- Frontend (Flask) en puerto 5000
- API Gateway (FastAPI) en puerto 8000
- Authentication Service (FastAPI) en puerto 8001
- Restaurantes Service (FastAPI) en puerto 8002
- Pedidos Service (FastAPI) en puerto 8003
- Repartidores Service (FastAPI) en puerto 8004

**Bases de Datos (5):**
- MongoDB para autenticación (puerto 27017)
- PostgreSQL para restaurantes (puerto 5432)
- PostgreSQL para pedidos (puerto 5433)
- PostgreSQL para repartidores (puerto 5435)
- Redis para cache/sesiones/coordinación (puerto 6379)

**Volúmenes (6):**
- Persistencia de datos de todas las bases de datos
- Almacenamiento de fotos de restaurantes

La comunicación interna utiliza **DNS de Docker**, permitiendo que los contenedores se refieran entre sí por nombre (ej: `api-gateway:8000`). El patrón **Database per Service** garantiza el aislamiento de datos. Los **depends_on** aseguran el orden correcto de inicio.
