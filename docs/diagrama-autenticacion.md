# Diagrama de Autenticación - Sistema Pedidos a Domicilio

## Arquitectura de Autenticación

```mermaid
graph TB
    Cliente[👤 Cliente/Usuario]
    Frontend[🌐 Frontend Flask<br/>Puerto 5000]
    Gateway[🚪 API Gateway<br/>Puerto 8000]
    AuthService[🔐 Servicio Auth<br/>Puerto 8001]
    MongoDB[(🍃 MongoDB<br/>auth_db)]
    Redis[(⚡ Redis<br/>Tokens)]
    OtrosServicios[📦 Otros Servicios<br/>Restaurantes/Pedidos/Repartidores]

    Cliente -->|1. Solicitud HTTP| Frontend
    Frontend -->|2. POST /api/v1/auth/*| Gateway
    Gateway -->|3. Forward| AuthService
    AuthService -->|4. Valida credenciales| MongoDB
    AuthService -->|5. Guarda refresh token| Redis
    AuthService -->|6. JWT tokens| Gateway
    Gateway -->|7. JWT tokens| Frontend
    Frontend -->|8. JWT tokens| Cliente

    Cliente -->|9. Request con Bearer Token| Frontend
    Frontend -->|10. Request + Token| Gateway
    Gateway -->|11. Valida JWT| Gateway
    Gateway -.->|12. Si válido: Forward| OtrosServicios
    Gateway -.->|Si inválido: 401| Frontend

    style AuthService fill:#ffd700,stroke:#333,stroke-width:3px
    style MongoDB fill:#4db33d,stroke:#333,stroke-width:2px,color:#fff
    style Redis fill:#dc382d,stroke:#333,stroke-width:2px,color:#fff
    style Gateway fill:#ff6b6b,stroke:#333,stroke-width:2px
```

---

## Flujo de Registro (Sign Up)

```mermaid
sequenceDiagram
    participant U as 👤 Usuario
    participant F as Frontend
    participant G as API Gateway
    participant A as Auth Service
    participant M as MongoDB

    U->>F: 1. Completa formulario registro<br/>(email, password, role)
    F->>G: 2. POST /api/v1/auth/register<br/>{email, password, role}
    Note over G: Ruta pública<br/>(sin autenticación)
    G->>A: 3. POST /register

    A->>M: 4. Busca email existente
    M-->>A: 5. Resultado búsqueda

    alt Email ya existe
        A-->>G: 409 Conflict<br/>"Email already registered"
        G-->>F: 409 Conflict
        F-->>U: ❌ Error: Email ya registrado
    else Password < 8 caracteres
        A-->>G: 400 Bad Request<br/>"Password too short"
        G-->>F: 400 Bad Request
        F-->>U: ❌ Error: Password muy corta
    else Registro exitoso
        A->>A: 6. Hash password (bcrypt)
        A->>M: 7. INSERT user document<br/>{email, password_hash, role, created_at}
        M-->>A: 8. Confirmación
        A-->>G: 200 OK<br/>{"message": "user created"}
        G-->>F: 200 OK
        F-->>U: ✅ Usuario creado<br/>Redirigir a login
    end
```

**Estructura del documento en MongoDB:**
```javascript
{
  "_id": ObjectId("..."),
  "email": "usuario@ejemplo.com",
  "password": "$pbkdf2-sha256$...",  // Hash bcrypt
  "role": "cliente",  // cliente | restaurante | repartidor
  "created_at": ISODate("2025-11-23T...")
}
```

---

## Flujo de Login (Sign In)

```mermaid
sequenceDiagram
    participant U as 👤 Usuario
    participant F as Frontend
    participant G as API Gateway
    participant A as Auth Service
    participant M as MongoDB
    participant R as Redis

    U->>F: 1. Ingresa email + password
    F->>G: 2. POST /api/v1/auth/login<br/>{email, password}
    Note over G: Ruta pública
    G->>A: 3. POST /login

    A->>M: 4. SELECT user WHERE email = ?
    M-->>A: 5. Documento del usuario

    alt Usuario no existe
        A-->>G: 401 Unauthorized<br/>"Incorrect email or password"
        G-->>F: 401 Unauthorized
        F-->>U: ❌ Credenciales incorrectas
    else Password incorrecta
        A->>A: 6. verify_password(plain, hash)
        A-->>G: 401 Unauthorized
        G-->>F: 401 Unauthorized
        F-->>U: ❌ Credenciales incorrectas
    else Login exitoso
        A->>A: 7. Genera Access Token (JWT)<br/>Expiración: 60 minutos
        A->>A: 8. Genera Refresh Token (JWT)<br/>Expiración: 7 días
        A->>R: 9. SETEX refresh:{jti}<br/>TTL: 7 días<br/>Value: user_id
        R-->>A: 10. OK
        A-->>G: 200 OK<br/>{access_token, refresh_token, token_type}
        G-->>F: 200 OK + Tokens
        F->>F: 11. Guarda tokens<br/>(localStorage/sessionStorage)
        F-->>U: ✅ Login exitoso<br/>Redirigir a dashboard
    end
```

**Tokens generados:**

### Access Token (JWT)
```json
{
  "sub": "673a21f0e4b0c8a9d1234567",  // user_id
  "email": "usuario@ejemplo.com",
  "role": "cliente",
  "exp": 1732395600  // Expira en 60 minutos
}
```

### Refresh Token (JWT)
```json
{
  "sub": "673a21f0e4b0c8a9d1234567",
  "email": "usuario@ejemplo.com",
  "role": "cliente",
  "jti": "550e8400-e29b-41d4-a716-446655440000",  // UUID único
  "exp": 1732999800  // Expira en 7 días
}
```

**Almacenamiento en Redis:**
```
Key: refresh:550e8400-e29b-41d4-a716-446655440000
Value: 673a21f0e4b0c8a9d1234567
TTL: 604800 segundos (7 días)
```

---

## Flujo de Peticiones Autenticadas

```mermaid
sequenceDiagram
    participant U as 👤 Usuario
    participant F as Frontend
    participant G as API Gateway
    participant S as Servicio<br/>(Restaurantes/Pedidos)

    U->>F: 1. Acción (ej: crear pedido)
    F->>F: 2. Lee access_token<br/>del localStorage
    F->>G: 3. POST /api/v1/pedidos/...<br/>Header: Authorization: Bearer {token}

    G->>G: 4. Verifica si ruta requiere auth

    alt Ruta pública (PUBLIC_ROUTES)
        Note over G: Rutas públicas:<br/>- auth:login<br/>- auth:register<br/>- restaurantes:*
        G->>S: 5. Forward sin validar token
    else Ruta protegida
        G->>G: 5. Extrae token del header<br/>Authorization: Bearer {token}

        alt Token ausente o malformado
            G-->>F: 401 Unauthorized<br/>"Missing Authorization header"
            F->>F: 6. Elimina tokens
            F-->>U: ❌ Redirigir a login
        else Token presente
            G->>G: 7. jwt.decode(token, SECRET_KEY)

            alt Token inválido o expirado
                G-->>F: 401 Unauthorized<br/>"Invalid token"
                F->>F: 8. Intenta refresh<br/>o redirige a login
                F-->>U: ❌ Sesión expirada
            else Token válido
                G->>G: 9. Extrae payload<br/>{sub, email, role}
                Note over G: Opcionalmente agrega<br/>X-User-Id, X-User-Role<br/>a headers
                G->>S: 10. Forward request + headers
                S-->>G: 11. Response
                G-->>F: 12. Response
                F-->>U: ✅ Acción completada
            end
        end
    end
```

---

## Flujo de Refresh Token

```mermaid
sequenceDiagram
    participant U as 👤 Usuario
    participant F as Frontend
    participant G as API Gateway
    participant A as Auth Service
    participant R as Redis

    Note over F: Access token expirado<br/>(después de 60 min)

    U->>F: 1. Intenta acción protegida
    F->>G: 2. Request con access_token expirado
    G-->>F: 401 Unauthorized

    F->>F: 3. Detecta 401<br/>Intenta renovar token
    F->>G: 4. POST /api/v1/auth/refresh<br/>{refresh_token}
    G->>A: 5. POST /refresh

    A->>A: 6. jwt.decode(refresh_token)
    A->>A: 7. Extrae jti y sub
    A->>R: 8. GET refresh:{jti}
    R-->>A: 9. user_id (si existe)

    alt Refresh token revocado o inválido
        A-->>G: 401 Unauthorized<br/>"Refresh token revoked"
        G-->>F: 401 Unauthorized
        F->>F: 10. Elimina todos los tokens
        F-->>U: ❌ Redirigir a login
    else Refresh token válido
        A->>A: 11. Genera nuevo access_token<br/>Expiración: 60 min
        A-->>G: 200 OK<br/>{access_token, token_type}
        G-->>F: 200 OK
        F->>F: 12. Actualiza access_token<br/>en localStorage
        F->>G: 13. Reintenta request original<br/>con nuevo token
        G-->>F: 14. Response exitoso
        F-->>U: ✅ Acción completada
    end
```

---

## Flujo de Logout

```mermaid
sequenceDiagram
    participant U as 👤 Usuario
    participant F as Frontend
    participant G as API Gateway
    participant A as Auth Service
    participant R as Redis

    U->>F: 1. Click "Cerrar sesión"
    F->>G: 2. POST /api/v1/auth/logout<br/>{refresh_token}
    G->>A: 3. POST /logout

    A->>A: 4. jwt.decode(refresh_token)
    A->>A: 5. Extrae jti
    A->>R: 6. DEL refresh:{jti}
    R-->>A: 7. 1 (key eliminada)

    A-->>G: 200 OK<br/>{"message": "logged out"}
    G-->>F: 200 OK
    F->>F: 8. Elimina tokens<br/>del localStorage
    F-->>U: ✅ Redirigir a página principal

    Note over R: Refresh token revocado<br/>No puede usarse para renovar
```

---

## Endpoints de Autenticación

### Públicos (sin autenticación requerida)

| Método | Ruta | Descripción | Request Body | Response |
|--------|------|-------------|--------------|----------|
| POST | `/register` | Registrar nuevo usuario | `{email, password, role?}` | `{message: "user created"}` |
| POST | `/login` | Iniciar sesión | `{email, password}` | `{access_token, refresh_token, token_type}` |
| POST | `/refresh` | Renovar access token | `{refresh_token}` | `{access_token, token_type}` |
| POST | `/logout` | Cerrar sesión | `{refresh_token}` | `{message: "logged out"}` |
| GET | `/health` | Health check | - | `{status: "ok"}` |

### Protegidos (requieren Bearer token)

| Método | Ruta | Descripción | Requiere Rol | Response |
|--------|------|-------------|--------------|----------|
| GET | `/me` | Datos del usuario actual | Cualquiera | `{user: {...}}` |
| GET | `/users` | Listar todos los usuarios | `admin` | `{users: [...]}` |
| GET | `/users/{user_id}` | Ver usuario específico | `admin` o el mismo usuario | `{user: {...}}` |

---

## Configuración de Rutas Públicas en API Gateway

El gateway determina qué rutas NO requieren autenticación mediante la variable de entorno `PUBLIC_ROUTES`:

```bash
PUBLIC_ROUTES="auth:login,auth:register,auth:health,restaurantes:*"
```

**Formato:** `servicio:ruta[*]`
- `auth:login` → Permite `/api/v1/auth/login`
- `auth:register` → Permite `/api/v1/auth/register`
- `restaurantes:*` → Permite **todas** las rutas de restaurantes (wildcard)

---

## Seguridad Implementada

### 🔒 Medidas de Seguridad

| Componente | Implementación |
|-----------|----------------|
| **Hashing de passwords** | PBKDF2-SHA256 vía Passlib |
| **Tokens JWT** | Firmados con HS256 + SECRET_KEY |
| **Access token TTL** | 60 minutos (corta vida) |
| **Refresh token TTL** | 7 días (revocable) |
| **Revocación de tokens** | Redis con TTL automático |
| **Validación centralizada** | En API Gateway |
| **Índices únicos** | Email único en MongoDB |
| **CORS configurado** | Middleware en Gateway |
| **Password mínimo** | 8 caracteres (validación backend) |

### 🔐 Almacenamiento de Secrets

```yaml
# Variables de entorno (.env)
JWT_SECRET=tu-secreto-super-seguro-cambiar-en-produccion
JWT_ALGORITHM=HS256
AUTH_DATABASE_URL=mongodb://auth-db:27017/auth_db
REDIS_URL=redis://redis:6379/0
```

⚠️ **Importante:** El `JWT_SECRET` debe ser el mismo en:
- Servicio de Autenticación (genera tokens)
- API Gateway (valida tokens)

---

## Flujo Completo: Desde Login hasta Acción Protegida

```mermaid
graph TD
    A[👤 Usuario ingresa credenciales] --> B[POST /login]
    B --> C{Credenciales válidas?}
    C -->|No| D[❌ 401 Unauthorized]
    C -->|Sí| E[Genera Access + Refresh Token]
    E --> F[Guarda refresh_token en Redis]
    F --> G[Retorna tokens al cliente]
    G --> H[Frontend guarda tokens]

    H --> I[Usuario crea pedido]
    I --> J[POST /pedidos con Bearer token]
    J --> K{Gateway valida token}
    K -->|Inválido| L[❌ 401 Unauthorized]
    K -->|Válido| M[Forward a servicio Pedidos]
    M --> N[Servicio procesa request]
    N --> O[✅ Pedido creado]

    O --> P{Access token expirado?}
    P -->|No| I
    P -->|Sí| Q[POST /refresh con refresh_token]
    Q --> R{Refresh válido en Redis?}
    R -->|No| S[❌ Redirigir a login]
    R -->|Sí| T[Nuevo access_token]
    T --> I

    style E fill:#90ee90
    style K fill:#ffd700
    style R fill:#ff6b6b
```

---

## Roles de Usuario

| Role | Descripción | Permisos |
|------|-------------|----------|
| **cliente** | Usuario final que hace pedidos | Crear pedidos, ver menús |
| **restaurante** | Dueño de restaurante | Gestionar menú, ver pedidos propios |
| **repartidor** | Delivery | Ver pedidos asignados, actualizar estado |
| **admin** | Administrador del sistema | Acceso completo (futuro) |

El rol se almacena en el token JWT y puede usarse en cada servicio para control de acceso específico.

---

## Diagrama de Estados del Token

```mermaid
stateDiagram-v2
    [*] --> Creado: Login exitoso
    Creado --> Activo: Token guardado en Redis
    Activo --> Válido: Dentro de TTL
    Activo --> Expirado: TTL cumplido (7 días)
    Activo --> Revocado: Logout manual

    Válido --> Renovado: Refresh exitoso
    Renovado --> Activo

    Expirado --> [*]
    Revocado --> [*]

    note right of Válido
        Access Token: 60 min
        Refresh Token: 7 días
    end note

    note right of Revocado
        Redis DEL refresh:{jti}
    end note
```

---

## Tecnologías Utilizadas

| Tecnología | Propósito | Versión |
|-----------|-----------|---------|
| **FastAPI** | Framework del servicio Auth | Latest |
| **PyMongo** | Cliente MongoDB | Latest |
| **python-jose** | Generación/validación JWT | Latest |
| **Passlib** | Hashing de passwords | Latest |
| **Redis** | Almacén de refresh tokens | 7+ |
| **MongoDB** | Base de datos de usuarios | 6+ |

---

**Última actualización**: Noviembre 2025
**Versión**: 1.0
