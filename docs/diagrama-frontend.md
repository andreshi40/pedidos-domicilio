# Diagrama del Frontend - Sistema Pedidos a Domicilio

## Arquitectura del Frontend

```mermaid
graph TB
    %% Frontend
    User[👤 Usuario<br/>Navegador Web]
    Frontend[🖥️ Frontend Flask<br/>Puerto 5000]

    %% API Gateway
    Gateway[🚪 API Gateway<br/>Puerto 8000]

    %% Microservicios
    Auth[🔐 Authentication<br/>:8001]
    Rest[🍽️ Restaurantes<br/>:8002]
    Ped[📦 Pedidos<br/>:8003]
    Rep[🚚 Repartidores<br/>:8004]

    %% MockStore
    Mock[📦 MockStore<br/>mock_data.json<br/>Fallback local]

    %% Flujo principal
    User -->|HTTP| Frontend
    Frontend -->|requests| Gateway
    Frontend -.->|fallback| Mock

    Gateway -->|Forward| Auth
    Gateway -->|Forward| Rest
    Gateway -->|Forward| Ped
    Gateway -->|Forward| Rep

    %% Estilos
    classDef frontend fill:#42a5f5,stroke:#333,stroke-width:3px,color:#fff
    classDef gateway fill:#ff9800,stroke:#333,stroke-width:2px,color:#fff
    classDef service fill:#66bb6a,stroke:#333,stroke-width:2px
    classDef mock fill:#ef5350,stroke:#333,stroke-width:2px,color:#fff
    classDef user fill:#7e57c2,stroke:#333,stroke-width:2px,color:#fff

    class Frontend frontend
    class Gateway gateway
    class Auth,Rest,Ped,Rep service
    class Mock mock
    class User user
```

---

## Flujo de Autenticación (Login)

```mermaid
sequenceDiagram
    participant User as Usuario
    participant Frontend as Frontend Flask
    participant Gateway as API Gateway
    participant Auth as Auth Service
    participant Session as Flask Session

    User->>+Frontend: GET /login
    Frontend-->>-User: Formulario de login

    User->>+Frontend: POST /login<br/>{email, password}

    alt Gateway disponible
        Frontend->>+Gateway: POST /api/v1/auth/login<br/>{email, password}
        Gateway->>+Auth: POST /login
        Auth-->>-Gateway: 200 {access_token, refresh_token}
        Gateway-->>-Frontend: 200 {access_token}
    else Gateway no disponible (fallback)
        Frontend->>+Auth: POST /login (directo)
        Auth-->>-Frontend: 200 {access_token, refresh_token}
    end

    Frontend->>Session: Guardar access_token
    Frontend->>Session: Guardar user_email
    Frontend-->>-User: Redirect a /

    Note over User,Session: Token guardado en sesión Flask
```

---

## Flujo de Registro de Usuario

```mermaid
sequenceDiagram
    participant User as Usuario
    participant Frontend as Frontend Flask
    participant Gateway as API Gateway
    participant Auth as Auth Service

    User->>+Frontend: GET /register
    Frontend-->>-User: Formulario de registro

    User->>+Frontend: POST /register<br/>{email, password, nombre, role}

    Frontend->>+Gateway: POST /api/v1/auth/register<br/>{user data}
    Gateway->>+Auth: POST /register

    alt Registro exitoso
        Auth-->>-Gateway: 201 {user_id, email}
        Gateway-->>-Frontend: 201 {user_id}
        Frontend-->>User: Flash "Registro exitoso"<br/>Redirect a /login
    else Usuario ya existe
        Auth-->>Gateway: 400 "Email already exists"
        Gateway-->>Frontend: 400
        Frontend-->>-User: Flash "Email ya registrado"
    end
```

---

## Flujo de Búsqueda de Restaurantes

```mermaid
sequenceDiagram
    participant User as Usuario
    participant Frontend as Frontend Flask
    participant Gateway as API Gateway
    participant Rest as Restaurantes Service
    participant Mock as MockStore

    User->>+Frontend: GET /?q=pizza

    alt Token en sesión
        Frontend->>Frontend: Obtener access_token
    end

    Frontend->>+Gateway: GET /api/v1/restaurantes?q=pizza<br/>Authorization: Bearer {token}

    alt Gateway responde OK
        Gateway->>+Rest: GET /api/v1/restaurantes?q=pizza
        Rest-->>-Gateway: 200 [{restaurantes}]
        Gateway-->>-Frontend: 200 [{restaurantes}]
        Frontend-->>-User: render index.html<br/>con lista de restaurantes
    else Error de conexión (fallback)
        Frontend->>+Mock: list_restaurantes()
        Mock-->>-Frontend: [{restaurantes locales}]
        Frontend-->>User: render con datos mock
    end
```

---

## Flujo de Visualización de Menú

```mermaid
sequenceDiagram
    participant User as Usuario
    participant Frontend as Frontend Flask
    participant Gateway as API Gateway
    participant Rest as Restaurantes Service

    User->>+Frontend: GET /restaurante/123

    Frontend->>Frontend: Validar token en sesión

    par Obtener info del restaurante
        Frontend->>+Gateway: GET /api/v1/restaurantes/123<br/>Authorization: Bearer {token}
        Gateway->>+Rest: GET /api/v1/restaurantes/123
        Rest-->>-Gateway: 200 {restaurante}
        Gateway-->>-Frontend: 200 {restaurante}
    and Obtener menú
        Frontend->>+Gateway: GET /api/v1/restaurantes/123/menu<br/>Authorization: Bearer {token}
        Gateway->>+Rest: GET /api/v1/restaurantes/123/menu
        Rest-->>-Gateway: 200 {menu: [items]}
        Gateway-->>-Frontend: 200 {menu}
    end

    Frontend-->>-User: render menu.html<br/>con items del menú
```

---

## Flujo de Creación de Pedido

```mermaid
sequenceDiagram
    participant User as Usuario
    participant Frontend as Frontend Flask
    participant Gateway as API Gateway
    participant Ped as Pedidos Service
    participant Rest as Restaurantes Service
    participant Rep as Repartidores Service

    User->>+Frontend: POST /pedido/crear<br/>{restaurante_id, items[], direccion}

    Frontend->>Frontend: Validar token en sesión
    Frontend->>Frontend: Construir OrderCreate

    Frontend->>+Gateway: POST /api/v1/pedidos<br/>Authorization: Bearer {token}<br/>{order data}
    Gateway->>Gateway: Validar JWT
    Gateway->>Gateway: Agregar X-User-* headers

    Gateway->>+Ped: POST /api/v1/pedidos<br/>+ user headers

    Note over Ped,Rep: Pedidos coordina con otros servicios

    Ped->>+Rest: GET /menu (validar stock)
    Rest-->>-Ped: 200 {menu}

    Ped->>+Rest: POST /reserve (reservar items)
    Rest-->>-Ped: 200 {reserved}

    Ped->>Ped: Persistir orden en PostgreSQL

    Ped->>+Rep: POST /assign-next
    Rep-->>-Ped: 200 {repartidor} o 204

    Ped-->>-Gateway: 201 {pedido creado}
    Gateway-->>-Frontend: 201 {pedido}

    Frontend-->>-User: Flash "Pedido creado"<br/>Redirect a /pedidos
```

---

## Flujo de Dashboard de Restaurante

```mermaid
sequenceDiagram
    participant User as Restaurante Owner
    participant Frontend as Frontend Flask
    participant Gateway as API Gateway
    participant Ped as Pedidos Service

    User->>+Frontend: GET /restaurante-dashboard

    Frontend->>Frontend: Validar role == "restaurante"
    Frontend->>Frontend: Obtener user_email de sesión

    Frontend->>+Gateway: GET /api/v1/restaurantes<br/>Authorization: Bearer {token}
    Gateway->>Rest: GET /api/v1/restaurantes
    Rest-->>Gateway: 200 [{restaurantes}]
    Gateway-->>Frontend: 200 [{restaurantes}]

    Frontend->>Frontend: Filtrar por user_email

    Frontend->>+Gateway: GET /api/v1/restaurante/{id}/orders<br/>?year=2025&month=11
    Gateway->>+Ped: GET /api/v1/restaurante/{id}/orders
    Ped-->>-Gateway: 200 {orders, stats_day, stats_month}
    Gateway-->>-Frontend: 200 {stats}

    Frontend-->>-User: render restaurante-dashboard.html<br/>con pedidos y estadísticas
```

---

## Flujo de Dashboard de Repartidor

```mermaid
sequenceDiagram
    participant User as Repartidor
    participant Frontend as Frontend Flask
    participant Gateway as API Gateway
    participant Rep as Repartidores Service
    participant Ped as Pedidos Service

    User->>+Frontend: GET /repartidor-dashboard

    Frontend->>Frontend: Validar role == "repartidor"

    Frontend->>+Gateway: GET /api/v1/repartidores<br/>Authorization: Bearer {token}
    Gateway->>+Rep: GET /api/v1/repartidores
    Rep-->>-Gateway: 200 [{repartidores}]
    Gateway-->>-Frontend: 200 [{repartidores}]

    Frontend->>Frontend: Filtrar por user_email

    Frontend->>+Gateway: GET /api/v1/repartidor/{id}/orders<br/>?year=2025&month=11
    Gateway->>+Ped: GET /api/v1/repartidor/{id}/orders
    Ped-->>-Gateway: 200 {orders, current_order, gain_current, gain_others}
    Gateway-->>-Frontend: 200 {data}

    Frontend-->>-User: render repartidor-dashboard.html<br/>con pedido actual y ganancias
```

---

## Sistema de Sesiones Flask

```mermaid
graph TB
    subgraph "Flask Session (server-side)"
        Token[access_token]
        Email[user_email]
        Role[user_role]
    end

    subgraph "Cookies del Navegador"
        SessionID[session_id<br/>firmado con secret_key]
    end

    User[Usuario] -->|Navegador| SessionID
    SessionID -->|Flask deserializa| Token
    SessionID -->|Flask deserializa| Email
    SessionID -->|Flask deserializa| Role

    Token -->|Authorization header| Gateway[API Gateway]

    style Token fill:#ff9800,color:#fff
    style SessionID fill:#42a5f5,color:#fff
    style Gateway fill:#ff9800,color:#fff
```

**Datos guardados en sesión:**
```python
session['access_token'] = "eyJhbGciOiJIUzI1NiIs..."
session['user_email'] = "cliente@example.com"
session['user_role'] = "cliente"  # o "restaurante" o "repartidor"
```

---

## MockStore: Sistema de Fallback

```mermaid
graph TB
    Frontend[Frontend Flask]

    Gateway{API Gateway<br/>disponible?}

    Services[Microservicios]

    Mock[MockStore<br/>mock_data.json]

    Frontend --> Gateway

    Gateway -->|Sí| Services
    Gateway -->|No / Timeout| Mock

    Mock --> Data[Datos locales:<br/>- restaurantes<br/>- menus<br/>- repartidores<br/>- orders]

    style Mock fill:#ef5350,color:#fff
    style Data fill:#ffab91,color:#333
```

**MockStore proporciona:**
- ✅ 2 restaurantes de prueba (Pizzeria, Sushi Bar)
- ✅ Menús con items y stock
- ✅ 1 repartidor disponible
- ✅ Persistencia en JSON local
- ✅ Operaciones CRUD básicas

**Cuándo se usa:**
- Gateway no disponible (timeout)
- Error de conexión
- Servicios caídos
- Desarrollo sin Docker

---

## Rutas del Frontend

```mermaid
graph LR
    subgraph "Rutas Públicas (sin token)"
        L[/login]
        R[/register]
        H[/health]
    end

    subgraph "Rutas de Cliente"
        I[/]
        Rest[/restaurante/:id]
        CP[/pedido/crear]
        LP[/pedidos]
    end

    subgraph "Rutas de Restaurante"
        RD[/restaurante-dashboard]
        ME[/restaurante/:id/menu/editar]
    end

    subgraph "Rutas de Repartidor"
        RepD[/repartidor-dashboard]
        Complete[/pedido/:id/complete]
    end

    subgraph "Rutas API (JSON)"
        Services[/_services]
    end

    style L,R,H fill:#66bb6a,color:#fff
    style I,Rest,CP,LP fill:#42a5f5,color:#fff
    style RD,ME fill:#ff9800,color:#fff
    style RepD,Complete fill:#ab47bc,color:#fff
    style Services fill:#26c6da,color:#fff
```

### Tabla de Rutas

| Ruta | Método | Requiere Token | Role | Descripción |
|------|--------|----------------|------|-------------|
| `/login` | GET/POST | No | - | Formulario de login |
| `/register` | GET/POST | No | - | Registro de usuario |
| `/` | GET | Opcional | - | Búsqueda de restaurantes |
| `/restaurante/<id>` | GET | Sí | - | Ver menú de restaurante |
| `/pedido/crear` | POST | Sí | cliente | Crear nuevo pedido |
| `/pedidos` | GET | Sí | cliente | Listar pedidos del cliente |
| `/restaurante-dashboard` | GET | Sí | restaurante | Dashboard con estadísticas |
| `/restaurante/<id>/menu/editar` | GET/POST | Sí | restaurante | Editar menú |
| `/repartidor-dashboard` | GET | Sí | repartidor | Dashboard de repartidor |
| `/pedido/<id>/complete` | POST | Sí | repartidor | Completar pedido |
| `/_services` | GET | Sí | - | Health check de servicios (JSON) |
| `/health` | GET | No | - | Health check del frontend |

---

## Manejo de Errores y Fallback

```mermaid
flowchart TD
    Start[Request al Gateway]

    Try[Intentar conexión]

    Start --> Try

    Try --> Success{Respuesta<br/>exitosa?}

    Success -->|Sí 200-299| Render[Renderizar con datos]

    Success -->|No 4xx| Error[Mostrar error al usuario<br/>flash message]

    Success -->|Timeout/500| Fallback{MockStore<br/>disponible?}

    Fallback -->|Sí| UseMock[Usar datos locales<br/>mock_data.json]
    Fallback -->|No| ShowError[Mostrar página de error]

    UseMock --> Render

    style Success fill:#ffc107,color:#333
    style Fallback fill:#ff9800,color:#fff
    style UseMock fill:#ef5350,color:#fff
    style Render fill:#66bb6a,color:#fff
```

**Estrategia de fallback por ruta:**
- **Login**: Intenta Gateway → Auth directo → Error
- **Restaurantes**: Intenta Gateway → MockStore → Lista vacía
- **Pedidos**: Intenta Gateway → MockStore → Error (no puede crear)
- **Dashboard**: Intenta Gateway → Error (requiere datos reales)

---

## Comunicación Frontend → Gateway

```mermaid
graph TB
    Frontend[Frontend Flask]

    subgraph "Headers enviados"
        Auth[Authorization: Bearer {token}]
        CT[Content-Type: application/json]
        Accept[Accept: application/json]
    end

    subgraph "Métodos HTTP"
        GET[GET - Consultas]
        POST[POST - Creación]
        PUT[PUT - Actualización]
        DELETE[DELETE - Eliminación]
    end

    Frontend --> Auth
    Frontend --> CT
    Frontend --> Accept

    Frontend --> GET
    Frontend --> POST
    Frontend --> PUT
    Frontend --> DELETE

    GET --> Gateway[API Gateway<br/>:8000/api/v1/...]
    POST --> Gateway
    PUT --> Gateway
    DELETE --> Gateway

    style Frontend fill:#42a5f5,color:#fff
    style Gateway fill:#ff9800,color:#fff
    style Auth fill:#f44336,color:#fff
```

**Ejemplo de request Python:**
```python
headers = {"Authorization": f"Bearer {session['access_token']}"}
response = requests.get(
    f"{API_GATEWAY_URL}/api/v1/restaurantes",
    headers=headers,
    timeout=5
)
```

---

## Templates HTML del Frontend

```mermaid
graph TB
    Base[base.html<br/>Layout principal]

    Base --> Index[index.html<br/>Lista restaurantes]
    Base --> Login[login.html<br/>Formulario login]
    Base --> Register[register.html<br/>Formulario registro]
    Base --> Menu[menu.html<br/>Menú del restaurante]
    Base --> Pedidos[pedidos.html<br/>Pedidos del cliente]
    Base --> RestDash[restaurante-dashboard.html<br/>Dashboard restaurante]
    Base --> RepDash[repartidor-dashboard.html<br/>Dashboard repartidor]
    Base --> Form[form.html<br/>Formularios genéricos]

    style Base fill:#42a5f5,color:#fff
    style Index,Menu,Pedidos fill:#66bb6a,color:#fff
    style Login,Register fill:#ffc107,color:#333
    style RestDash,RepDash fill:#ff9800,color:#fff
```

**Estructura base.html:**
- Navbar con links según role
- Sistema de flash messages
- Logout button
- CSS de Bootstrap/custom

---

## Flujo Completo: Cliente Crea Pedido

```mermaid
sequenceDiagram
    participant User as Cliente
    participant Browser as Navegador
    participant Frontend as Frontend Flask
    participant Gateway as API Gateway
    participant Auth as Auth Service
    participant Rest as Restaurantes Service
    participant Ped as Pedidos Service
    participant Rep as Repartidores Service

    Note over User,Rep: 1. Usuario se autentica
    User->>Browser: Abrir /login
    Browser->>+Frontend: GET /login
    Frontend-->>-Browser: Formulario login
    User->>Browser: Ingresar credenciales
    Browser->>+Frontend: POST /login
    Frontend->>+Gateway: POST /api/v1/auth/login
    Gateway->>+Auth: POST /login
    Auth-->>-Gateway: 200 {access_token}
    Gateway-->>-Frontend: 200 {token}
    Frontend->>Frontend: session['access_token'] = token
    Frontend-->>-Browser: Redirect /

    Note over User,Rep: 2. Usuario busca restaurante
    Browser->>+Frontend: GET /?q=pizza
    Frontend->>+Gateway: GET /api/v1/restaurantes?q=pizza<br/>+ Bearer token
    Gateway->>+Rest: GET /api/v1/restaurantes?q=pizza
    Rest-->>-Gateway: 200 [{restaurantes}]
    Gateway-->>-Frontend: 200 [{restaurantes}]
    Frontend-->>-Browser: render index.html

    Note over User,Rep: 3. Usuario ve menú
    User->>Browser: Click en restaurante
    Browser->>+Frontend: GET /restaurante/123
    Frontend->>+Gateway: GET /api/v1/restaurantes/123/menu
    Gateway->>+Rest: GET /api/v1/restaurantes/123/menu
    Rest-->>-Gateway: 200 {menu}
    Gateway-->>-Frontend: 200 {menu}
    Frontend-->>-Browser: render menu.html

    Note over User,Rep: 4. Usuario crea pedido
    User->>Browser: Agregar items, enviar form
    Browser->>+Frontend: POST /pedido/crear<br/>{restaurante, items, direccion}
    Frontend->>+Gateway: POST /api/v1/pedidos<br/>+ Bearer token
    Gateway->>+Ped: POST /api/v1/pedidos<br/>+ X-User-* headers

    Ped->>+Rest: Validar stock y reservar
    Rest-->>-Ped: 200 {reserved}

    Ped->>+Rep: Asignar repartidor
    Rep-->>-Ped: 200 {repartidor}

    Ped-->>-Gateway: 201 {pedido creado}
    Gateway-->>-Frontend: 201 {pedido}
    Frontend-->>-Browser: Flash "Pedido creado"<br/>Redirect /pedidos
```

---

## Variables de Entorno

```mermaid
graph TB
    subgraph "Variables de Configuración"
        API[API_GATEWAY_URL<br/>default: http://localhost:8000]
        Secret[FLASK_SECRET<br/>default: dev-secret-change-me]
    end

    subgraph "Frontend Flask"
        App[Flask App]
        Session[Session Manager]
    end

    API --> App
    Secret --> Session

    App --> Requests[requests.get/post]
    Session --> Cookies[Secure Cookies]

    style API fill:#ff9800,color:#fff
    style Secret fill:#f44336,color:#fff
```

---

## Ventajas de esta Arquitectura

```mermaid
mindmap
  root((Frontend Flask))
    Simplicidad
      Templates Jinja2 server-side
      Sesiones Flask integradas
      Sin framework JS complejo
      Renderizado rápido

    Resiliencia
      MockStore fallback
      Manejo de timeouts
      Fallback directo a servicios
      Mensajes flash de error

    Seguridad
      Token en sesión server-side
      No expone token al JS
      Secret key para cookies
      HTTPS en producción

    Experiencia
      UI responsiva Bootstrap
      Flash messages
      Dashboards por role
      Búsqueda en tiempo real
```

---

## Tecnologías del Frontend

| Componente | Tecnología | Propósito |
|-----------|------------|-----------|
| Framework Web | Flask | Renderizado de templates |
| Templates | Jinja2 | HTML dinámico |
| Sesiones | Flask Session | Almacenar token/user info |
| HTTP Client | requests | Llamadas al Gateway |
| CSS | Bootstrap + custom | Estilos responsivos |
| Fallback | MockStore (JSON) | Datos locales cuando servicios caen |
| Deployment | Docker | Contenedor en puerto 5000 |

---

**Última actualización**: Noviembre 2025
**Versión**: 1.0
**Puerto**: 5000
