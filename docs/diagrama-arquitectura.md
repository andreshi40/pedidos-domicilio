# Diagrama de Arquitectura - Sistema Pedidos a Domicilio

## Flujo de Interacción de Componentes

```mermaid
graph TB
    %% Usuarios
    Cliente[👤 Cliente Web]

    %% Frontend
    Frontend[🖥️ Frontend Flask<br/>Puerto 5000]

    %% API Gateway
    Gateway[🚪 API Gateway<br/>FastAPI - Puerto 8000]

    %% Servicio de Autenticación
    Auth[🔐 Servicio Autenticación<br/>FastAPI - Puerto 8001]
    AuthDB[(🗄️ MongoDB<br/>auth_db)]

    %% Microservicios
    Restaurantes[🍽️ Servicio Restaurantes<br/>FastAPI - Puerto 8002]
    RestDB[(🗄️ PostgreSQL<br/>service1_db)]

    Pedidos[📦 Servicio Pedidos<br/>FastAPI - Puerto 8003]
    PedidosDB[(🗄️ PostgreSQL<br/>pedidos_db)]
    Redis[(⚡ Redis<br/>Cache)]

    Repartidores[🚚 Servicio Repartidores<br/>FastAPI - Puerto 8004]
    RepartidoresDB[(🗄️ PostgreSQL<br/>repartidores_db)]

    %% Flujos de comunicación
    Cliente -->|HTTP| Frontend
    Frontend -->|HTTP API| Gateway

    Gateway -->|Validar JWT| Auth
    Gateway -->|CRUD Restaurantes| Restaurantes
    Gateway -->|CRUD Pedidos| Pedidos
    Gateway -->|CRUD Repartidores| Repartidores

    Auth -->|R/W| AuthDB
    Restaurantes -->|R/W| RestDB
    Pedidos -->|R/W| PedidosDB
    Pedidos -->|Cache| Redis
    Repartidores -->|R/W| RepartidoresDB

    %% Estilos
    classDef frontend fill:#61dafb,stroke:#333,stroke-width:2px,color:#000
    classDef gateway fill:#ff6b6b,stroke:#333,stroke-width:3px,color:#fff
    classDef auth fill:#ffd93d,stroke:#333,stroke-width:2px,color:#000
    classDef service fill:#6bcf7f,stroke:#333,stroke-width:2px,color:#000
    classDef database fill:#a29bfe,stroke:#333,stroke-width:2px,color:#000
    classDef user fill:#fd79a8,stroke:#333,stroke-width:2px,color:#fff

    class Cliente user
    class Frontend frontend
    class Gateway gateway
    class Auth auth
    class Restaurantes,Pedidos,Repartidores service
    class AuthDB,RestDB,PedidosDB,RepartidoresDB,Redis database
```

## Flujo Detallado de Operaciones

```mermaid
sequenceDiagram
    participant C as 👤 Cliente
    participant F as 🖥️ Frontend
    participant G as 🚪 Gateway
    participant A as 🔐 Auth
    participant R as 🍽️ Restaurantes
    participant P as 📦 Pedidos
    participant D as 🚚 Repartidores

    %% Registro y Login
    rect rgb(255, 240, 220)
        Note over C,A: 1. Autenticación
        C->>F: Registro/Login
        F->>G: POST /auth/register o /login
        G->>A: Validar credenciales
        A-->>G: JWT Token
        G-->>F: Token + User Info
        F-->>C: Sesión iniciada
    end

    %% Buscar Restaurantes
    rect rgb(220, 240, 255)
        Note over C,R: 2. Búsqueda de Restaurantes
        C->>F: Buscar restaurantes
        F->>G: GET /restaurante (con JWT)
        G->>A: Validar JWT
        A-->>G: Usuario válido
        G->>R: Listar restaurantes
        R-->>G: Lista de restaurantes
        G-->>F: Restaurantes + Menús
        F-->>C: Mostrar opciones
    end

    %% Crear Pedido
    rect rgb(220, 255, 220)
        Note over C,P: 3. Creación de Pedido
        C->>F: Crear pedido (items + dirección)
        F->>G: POST /pedidos (con JWT)
        G->>A: Validar JWT
        A-->>G: Usuario válido
        G->>P: Crear pedido + Reservar stock
        P->>R: Verificar/Reservar items
        R-->>P: Stock reservado
        P-->>G: Pedido creado (estado: creado)
        G-->>F: Pedido confirmado
        F-->>C: Confirmación + ID pedido
    end

    %% Asignar Repartidor
    rect rgb(255, 220, 255)
        Note over P,D: 4. Asignación Automática
        P->>D: Buscar repartidor disponible
        D->>D: SELECT FOR UPDATE SKIP LOCKED
        D-->>P: Repartidor asignado
        P->>P: Actualizar estado: asignado
    end

    %% Completar Entrega
    rect rgb(255, 255, 220)
        Note over C,D: 5. Entrega y Finalización
        C->>F: Consultar estado pedido
        F->>G: GET /pedidos/{id}
        G->>P: Obtener estado
        P-->>G: Estado: asignado + Info repartidor
        G-->>F: Datos completos
        F-->>C: Mostrar tracking

        D->>G: POST /pedidos/{id}/complete
        G->>P: Completar pedido
        P->>D: Liberar repartidor
        P->>P: Estado: completado
    end
```

## Descripción de Componentes

### 🖥️ Frontend (Flask - Puerto 5000)
- Interfaz web responsive
- Dashboards por rol (Cliente, Restaurante, Repartidor)
- Manejo de sesiones JWT
- Polling para actualizaciones en tiempo real

### 🚪 API Gateway (FastAPI - Puerto 8000)
- **Punto único de entrada** para todas las peticiones
- Validación centralizada de JWT
- Enrutamiento a microservicios
- Inyección de headers `X-User-Id` y `X-User-Email`

### 🔐 Servicio de Autenticación (Puerto 8001)
- Registro de usuarios (Cliente, Restaurante, Repartidor)
- Generación de tokens JWT
- Validación de credenciales con bcrypt
- Base de datos: MongoDB

### 🍽️ Servicio de Restaurantes (Puerto 8002)
- CRUD de restaurantes y menús
- Control de stock en tiempo real
- Upload y serving de imágenes
- Base de datos: PostgreSQL

### 📦 Servicio de Pedidos (Puerto 8003)
- Creación de pedidos con reserva atómica
- Gestión de estados: `creado` → `asignado` → `completado`
- Estadísticas de ventas por restaurante
- Base de datos: PostgreSQL + Redis

### 🚚 Servicio de Repartidores (Puerto 8004)
- CRUD de repartidores
- Asignación atómica con `SELECT FOR UPDATE SKIP LOCKED`
- Background thread para asignación automática
- Base de datos: PostgreSQL

## Tecnologías Utilizadas

| Componente | Tecnología | Puerto |
|-----------|-----------|--------|
| Frontend | Flask + Jinja2 | 5000 |
| API Gateway | FastAPI | 8000 |
| Autenticación | FastAPI + MongoDB | 8001 |
| Restaurantes | FastAPI + PostgreSQL | 8002 |
| Pedidos | FastAPI + PostgreSQL + Redis | 8003 |
| Repartidores | FastAPI + PostgreSQL | 8004 |

## Patrones de Arquitectura

- ✅ **Microservicios**: Servicios independientes con bases de datos dedicadas
- ✅ **API Gateway Pattern**: Punto único de entrada y autenticación centralizada
- ✅ **Database per Service**: Cada microservicio con su propia BD
- ✅ **JWT Authentication**: Autenticación stateless con tokens
- ✅ **Atomic Operations**: Transacciones ACID con `SELECT FOR UPDATE`
