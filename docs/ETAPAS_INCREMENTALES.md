# Etapas Incrementales del Proyecto Pedidos-Domicilio

Este documento define las etapas de desarrollo del proyecto "pedidos-domicilio" siguiendo la **metodología incremental**. Cada etapa representa un incremento funcional que añade valor al sistema y puede ser probado, revisado y desplegado de forma independiente.

## Índice
1. [Introducción a la Metodología Incremental](#introducción-a-la-metodología-incremental)
2. [Visión General del Proyecto](#visión-general-del-proyecto)
3. [Etapas de Desarrollo](#etapas-de-desarrollo)
4. [Cronograma Sugerido](#cronograma-sugerido)
5. [Criterios de Éxito por Etapa](#criterios-de-éxito-por-etapa)

---

## Introducción a la Metodología Incremental

La metodología incremental es un enfoque de desarrollo de software donde el sistema se construye y entrega en incrementos sucesivos. Cada incremento:

- **Añade funcionalidad nueva** al sistema existente
- **Es funcional y probado** de manera independiente
- **Puede ser desplegado** en producción (o ambiente de pruebas)
- **Permite retroalimentación temprana** del usuario/cliente
- **Reduce riesgos** al validar componentes progresivamente

### Ventajas en este proyecto:
- Permite validar la arquitectura de microservicios gradualmente
- Facilita la detección temprana de problemas de integración
- Posibilita entregas parciales funcionales
- Reduce la complejidad al enfocarse en un subconjunto del sistema en cada iteración

---

## Visión General del Proyecto

**Sistema de Pedidos a Domicilio** basado en microservicios que permite:
- Gestionar restaurantes y sus menús
- Crear y gestionar pedidos de clientes
- Asignar repartidores disponibles a pedidos
- Autenticar usuarios en el sistema

**Arquitectura:**
- Frontend: Flask (interfaz web)
- API Gateway: FastAPI (enrutamiento y autenticación)
- Microservicios: Authentication, Restaurantes, Pedidos, Repartidores
- Bases de datos: MongoDB (auth), PostgreSQL (servicios), Redis (caché/coordinación)
- Orquestación: Docker Compose

---

## Etapas de Desarrollo

### **Etapa 0: Configuración Inicial e Infraestructura Base**
**Duración estimada:** 1-2 semanas  
**Objetivo:** Establecer la base del proyecto y el ambiente de desarrollo

#### Componentes a implementar:
1. **Estructura del proyecto**
   - Creación de directorios para microservicios
   - Configuración de repositorio Git
   - Setup de `.env` y variables de entorno
   - Documentación básica (README.md)

2. **Infraestructura Docker**
   - Configuración de `docker-compose.yml`
   - Definición de servicios base (sin lógica)
   - Setup de bases de datos (PostgreSQL, MongoDB, Redis)
   - Verificación de conectividad entre contenedores

3. **Frontend básico**
   - Aplicación Flask con estructura base
   - Página de inicio simple
   - Configuración de templates (Jinja2)

4. **API Gateway esqueleto**
   - Servidor FastAPI básico
   - Health check endpoint (`/health`)
   - Configuración de CORS

#### Entregables:
- [ ] Docker Compose levanta todos los contenedores
- [ ] Frontend accesible en `http://localhost:5000`
- [ ] API Gateway responde en `http://localhost:8000/health`
- [ ] Bases de datos inicializadas y accesibles
- [ ] Documentación de setup en README.md

#### Criterios de aceptación:
- ✓ `docker-compose up --build` ejecuta sin errores
- ✓ Todos los contenedores están en estado "running"
- ✓ Se puede acceder al frontend desde el navegador
- ✓ Conexiones a bases de datos funcionan correctamente

---

### **Etapa 1: Servicio de Autenticación (MVP)**
**Duración estimada:** 1-2 semanas  
**Objetivo:** Implementar autenticación básica con JWT

#### Componentes a implementar:
1. **Microservicio de Autenticación**
   - Servidor FastAPI en puerto 8001
   - Modelo de usuario en MongoDB (email, password hash, rol)
   - Endpoint POST `/api/v1/auth/register` (registro de usuarios)
   - Endpoint POST `/api/v1/auth/login` (autenticación y generación de JWT)
   - Endpoint GET `/api/v1/auth/me` (obtener usuario actual)
   - Hash de contraseñas con bcrypt/passlib
   - Generación de tokens JWT con python-jose

2. **Integración con API Gateway**
   - Middleware de validación JWT en gateway
   - Forward de peticiones `/api/v1/auth/*` al servicio de auth
   - Inyección de información de usuario en headers internos
   - Lista de rutas públicas (PUBLIC_ROUTES)

3. **Frontend - Autenticación**
   - Formulario de registro
   - Formulario de login
   - Almacenamiento de JWT en sesión/cookies
   - Pantalla de perfil de usuario
   - Manejo de sesión expirada

#### Entregables:
- [ ] Usuarios pueden registrarse
- [ ] Usuarios pueden hacer login y recibir JWT
- [ ] Gateway valida JWT en rutas protegidas
- [ ] Frontend muestra información del usuario autenticado
- [ ] Tests unitarios del servicio de autenticación

#### Criterios de aceptación:
- ✓ POST `/api/v1/auth/register` crea usuario en MongoDB
- ✓ POST `/api/v1/auth/login` retorna JWT válido
- ✓ GET `/api/v1/auth/me` con token retorna datos del usuario
- ✓ Peticiones sin token a rutas protegidas retornan 401
- ✓ Frontend permite login/logout completo

#### Dependencias:
- Requiere: Etapa 0 completada

---

### **Etapa 2: Servicio de Restaurantes (Gestión de Catálogo)**
**Duración estimada:** 2-3 semanas  
**Objetivo:** Implementar gestión de restaurantes y sus menús

#### Componentes a implementar:
1. **Microservicio de Restaurantes**
   - Servidor FastAPI en puerto 8002
   - Modelo de datos en PostgreSQL:
     - Tabla `restaurantes` (id, nombre, descripción, dirección, teléfono, foto)
     - Tabla `menu_items` (id, restaurante_id, nombre, descripción, precio, stock, categoría)
   - Endpoints CRUD:
     - GET `/api/v1/restaurantes` (listar restaurantes)
     - GET `/api/v1/restaurantes/{id}` (detalle de restaurante)
     - POST `/api/v1/restaurantes` (crear restaurante - admin)
     - PUT `/api/v1/restaurantes/{id}` (actualizar - admin)
     - GET `/api/v1/restaurantes/{id}/menu` (obtener menú)
     - POST `/api/v1/restaurantes/{id}/menu` (añadir ítem - admin)
     - PUT `/api/v1/restaurantes/{id}/menu/{item_id}` (actualizar ítem)
     - POST `/api/v1/restaurantes/{rid}/menu/{item}/reserve` (reservar stock)
     - POST `/api/v1/restaurantes/{rid}/menu/{item}/release` (liberar stock)

2. **Integración con API Gateway**
   - Forward de peticiones `/api/v1/restaurantes/*`
   - Validación de roles (admin vs usuario)

3. **Frontend - Restaurantes**
   - Vista de listado de restaurantes (cards con foto)
   - Vista de detalle de restaurante con menú
   - Vista de administración (crear/editar restaurantes - solo admin)
   - Vista de gestión de menú (añadir/editar ítems - admin)
   - Búsqueda y filtros básicos

4. **Gestión de Stock**
   - Implementación de reserva y liberación de stock
   - Validaciones de stock disponible
   - Transacciones para asegurar consistencia

#### Entregables:
- [ ] CRUD completo de restaurantes
- [ ] CRUD completo de menú
- [ ] Sistema de reserva/liberación de stock
- [ ] Frontend con vistas de restaurantes y menús
- [ ] Panel de administración para gestión de catálogo
- [ ] Tests de integración de endpoints
- [ ] Datos de ejemplo (seed) con 3-5 restaurantes

#### Criterios de aceptación:
- ✓ Se pueden crear y listar restaurantes
- ✓ Cada restaurante tiene menú con múltiples ítems
- ✓ Stock se puede reservar y liberar correctamente
- ✓ Usuarios ven catálogo en frontend
- ✓ Solo admins pueden modificar restaurantes/menú
- ✓ Imágenes de restaurantes se almacenan y muestran

#### Dependencias:
- Requiere: Etapa 1 completada (para autorización)

---

### **Etapa 3: Servicio de Repartidores (Gestión de Flota)**
**Duración estimada:** 1-2 semanas  
**Objetivo:** Implementar gestión de repartidores y asignación

#### Componentes a implementar:
1. **Microservicio de Repartidores**
   - Servidor FastAPI en puerto 8004
   - Modelo de datos en PostgreSQL:
     - Tabla `repartidores` (id, nombre, teléfono, email, estado, ubicación_actual)
     - Estados: `disponible`, `ocupado`, `desconectado`
   - Endpoints:
     - GET `/api/v1/repartidores` (listar repartidores)
     - GET `/api/v1/repartidores/{id}` (detalle de repartidor)
     - POST `/api/v1/repartidores` (registrar repartidor - admin)
     - PUT `/api/v1/repartidores/{id}` (actualizar repartidor)
     - PATCH `/api/v1/repartidores/{id}/estado` (cambiar estado)
     - POST `/api/v1/repartidores/assign-next` (asignar repartidor disponible - interno)

2. **Sistema de Asignación**
   - Endpoint atómico de asignación usando `SELECT FOR UPDATE SKIP LOCKED`
   - Lógica de selección (FIFO o criterios como ubicación)
   - Cambio automático de estado a "ocupado" al asignar

3. **Integración con API Gateway**
   - Forward de peticiones `/api/v1/repartidores/*`
   - Protección del endpoint `/assign-next` (solo interno)

4. **Frontend - Repartidores**
   - Vista de listado de repartidores (admin)
   - Dashboard con estado de repartidores
   - Formulario de registro de repartidor (admin)
   - Indicadores visuales de estado (disponible/ocupado/desconectado)

#### Entregables:
- [ ] CRUD de repartidores
- [ ] Sistema de cambio de estados
- [ ] Endpoint de asignación atómica
- [ ] Frontend con gestión de repartidores
- [ ] Tests de concurrencia para asignación
- [ ] Datos de ejemplo con 5-10 repartidores

#### Criterios de aceptación:
- ✓ Se pueden registrar y listar repartidores
- ✓ Estados se actualizan correctamente
- ✓ Asignación es atómica (sin race conditions)
- ✓ Solo repartidores "disponibles" se pueden asignar
- ✓ Frontend muestra estado actual de cada repartidor

#### Dependencias:
- Requiere: Etapa 1 completada (para autorización)

---

### **Etapa 4: Servicio de Pedidos (Flujo Principal)**
**Duración estimada:** 3-4 semanas  
**Objetivo:** Implementar creación y gestión de pedidos con integración completa

#### Componentes a implementar:
1. **Microservicio de Pedidos**
   - Servidor FastAPI en puerto 8003
   - Modelo de datos en PostgreSQL:
     - Tabla `pedidos` (id, restaurante_id, cliente_email, dirección, estado, repartidor_id, repartidor_snapshot, fecha_creacion, fecha_asignacion)
     - Tabla `order_items` (id, pedido_id, item_id, nombre, precio, cantidad)
     - Estados: `creado`, `asignado`, `en_camino`, `entregado`, `cancelado`
   - Endpoints:
     - POST `/api/v1/pedidos` (crear pedido)
     - GET `/api/v1/pedidos` (listar pedidos del usuario)
     - GET `/api/v1/pedidos/{id}` (detalle de pedido)
     - PATCH `/api/v1/pedidos/{id}/estado` (actualizar estado)
     - GET `/api/v1/pedidos/admin/todos` (listar todos - admin)

2. **Lógica de Creación de Pedidos**
   - Validación de ítems y stock en servicio de restaurantes
   - Reserva de stock para cada ítem del pedido
   - Persistencia del pedido con snapshot de información
   - Intento de asignación inmediata de repartidor
   - Rollback de reservas si falla algún paso
   - Manejo de transacciones distribuidas

3. **Background Assigner**
   - Proceso en background que reintenta asignaciones
   - Busca pedidos en estado "creado" sin repartidor
   - Intenta asignar repartidor cada N segundos
   - Usa Redis para coordinación/locks

4. **Comunicación entre Servicios**
   - Cliente HTTP para llamar a restaurantes-service
   - Cliente HTTP para llamar a repartidores-service
   - Manejo de timeouts y errores
   - Lógica de compensación (saga pattern básico)

5. **Integración con API Gateway**
   - Forward de peticiones `/api/v1/pedidos/*`

6. **Frontend - Pedidos**
   - Formulario de creación de pedido
     - Selección de restaurante
     - Selección de ítems del menú con cantidad
     - Datos de entrega (dirección, contacto)
   - Vista de confirmación de pedido
   - Vista de listado de pedidos del usuario
   - Vista de detalle de pedido con tracking
   - Vista de administración de todos los pedidos (admin)
   - Actualización de estado del pedido

#### Entregables:
- [ ] Flujo completo de creación de pedido
- [ ] Reserva/liberación de stock funcional
- [ ] Asignación automática de repartidor
- [ ] Background assigner para pedidos sin asignar
- [ ] Frontend con carrito y checkout
- [ ] Vista de tracking de pedido
- [ ] Tests de integración end-to-end
- [ ] Tests de escenarios de fallo (sin stock, sin repartidor)

#### Criterios de aceptación:
- ✓ Se puede crear pedido con múltiples ítems
- ✓ Stock se reserva correctamente en restaurantes
- ✓ Repartidor se asigna si hay disponible
- ✓ Pedido queda en "creado" si no hay repartidor disponible
- ✓ Background assigner asigna repartidores cuando se liberan
- ✓ Rollback funciona si falla reserva de algún ítem
- ✓ Usuario ve estado actualizado de su pedido
- ✓ Admin puede ver y gestionar todos los pedidos

#### Dependencias:
- Requiere: Etapas 1, 2 y 3 completadas

---

### **Etapa 5: Mejoras de UX y Funcionalidades Avanzadas**
**Duración estimada:** 2-3 semanas  
**Objetivo:** Pulir la experiencia de usuario y añadir funcionalidades complementarias

#### Componentes a implementar:
1. **Mejoras de Frontend**
   - Dashboard del usuario con historial de pedidos
   - Sistema de notificaciones en tiempo real (opcional: WebSockets)
   - Búsqueda avanzada de restaurantes (por categoría, precio, rating)
   - Filtros en menú (vegetariano, sin gluten, etc.)
   - Carrito de compras persistente (localStorage)
   - Diseño responsive (mobile-first)
   - Mejoras en UX/UI (loading states, animaciones)

2. **Valoraciones y Comentarios**
   - Sistema de rating para restaurantes (1-5 estrellas)
   - Comentarios de usuarios sobre pedidos
   - Visualización de ratings promedio
   - Moderación de comentarios (admin)

3. **Mejoras en Tracking**
   - Estados más detallados del pedido:
     - `creado` → `confirmado` → `preparando` → `listo_para_entrega` → `en_camino` → `entregado`
   - Timeline visual del pedido
   - Estimación de tiempo de entrega
   - Información del repartidor asignado

4. **Panel de Administración Mejorado**
   - Dashboard con métricas (pedidos por día, ingresos, etc.)
   - Visualización de estadísticas de restaurantes
   - Gestión de usuarios y roles
   - Reportes exportables (CSV, PDF)

5. **Notificaciones y Alertas**
   - Emails de confirmación de pedido
   - Notificaciones de cambio de estado
   - Alertas para admins (stock bajo, problemas de asignación)

#### Entregables:
- [ ] Sistema de ratings y comentarios funcional
- [ ] Dashboard de usuario con historial
- [ ] Panel de administración con métricas
- [ ] Mejoras de UX en todo el frontend
- [ ] Sistema de notificaciones
- [ ] Diseño responsive

#### Criterios de aceptación:
- ✓ Usuarios pueden valorar y comentar restaurantes
- ✓ Dashboard muestra métricas relevantes
- ✓ Frontend es responsive en móvil y desktop
- ✓ Notificaciones llegan en eventos importantes
- ✓ Tracking de pedido es claro y visual

#### Dependencias:
- Requiere: Etapa 4 completada

---

### **Etapa 6: Optimización, Seguridad y Producción**
**Duración estimada:** 2-3 semanas  
**Objetivo:** Preparar el sistema para producción

#### Componentes a implementar:
1. **Optimización de Rendimiento**
   - Implementación de caché con Redis
     - Caché de menús frecuentemente consultados
     - Caché de listado de restaurantes
   - Índices en bases de datos
   - Paginación en listados grandes
   - Lazy loading de imágenes
   - Optimización de queries SQL

2. **Seguridad**
   - Rate limiting en API Gateway
   - Validación estricta de inputs (Pydantic)
   - Sanitización de datos
   - HTTPS en producción
   - Secrets management (no hardcodear passwords)
   - Protección contra SQL injection
   - CORS configurado correctamente
   - Headers de seguridad (CSP, X-Frame-Options, etc.)

3. **Logging y Monitoreo**
   - Logging estructurado en todos los servicios
   - Centralización de logs
   - Health checks avanzados
   - Métricas de performance
   - Alertas automáticas

4. **Testing Avanzado**
   - Tests de carga (locust, k6)
   - Tests de seguridad (OWASP checks)
   - Tests end-to-end automatizados
   - Cobertura de código >80%

5. **Documentación**
   - API documentation con Swagger/OpenAPI
   - Guía de despliegue
   - Guía de troubleshooting
   - Arquitectura actualizada
   - Manual de usuario

6. **CI/CD**
   - Pipeline de GitHub Actions
   - Tests automáticos en PRs
   - Linting y formateo de código
   - Build automático de imágenes Docker
   - Deploy automático a staging

7. **Preparación para Producción**
   - Variables de entorno para diferentes ambientes
   - Configuración de backups automáticos
   - Plan de recuperación ante desastres
   - Configuración de balanceo de carga (opcional)

#### Entregables:
- [ ] Sistema con caché implementado
- [ ] Auditoría de seguridad completada
- [ ] Logging y monitoreo funcional
- [ ] Suite completa de tests
- [ ] Documentación completa
- [ ] Pipeline CI/CD configurado
- [ ] Sistema listo para despliegue en producción

#### Criterios de aceptación:
- ✓ Respuesta de API <500ms en el 95% de peticiones
- ✓ Tests de seguridad pasan sin issues críticos
- ✓ Cobertura de tests >80%
- ✓ Documentación API completa y actualizada
- ✓ Pipeline CI/CD ejecuta y despliega correctamente
- ✓ Sistema puede recuperarse de fallos

#### Dependencias:
- Requiere: Etapa 5 completada

---

## Cronograma Sugerido

| Etapa | Duración | Inicio | Fin | Acumulado |
|-------|----------|--------|-----|-----------|
| Etapa 0: Infraestructura Base | 1-2 sem | Sem 1 | Sem 2 | 2 sem |
| Etapa 1: Autenticación | 1-2 sem | Sem 3 | Sem 4 | 4 sem |
| Etapa 2: Restaurantes | 2-3 sem | Sem 5 | Sem 7 | 7 sem |
| Etapa 3: Repartidores | 1-2 sem | Sem 8 | Sem 9 | 9 sem |
| Etapa 4: Pedidos (Core) | 3-4 sem | Sem 10 | Sem 13 | 13 sem |
| Etapa 5: Mejoras UX | 2-3 sem | Sem 14 | Sem 16 | 16 sem |
| Etapa 6: Producción | 2-3 sem | Sem 17 | Sem 19 | 19 sem |

**Duración total estimada:** 19-20 semanas (≈5 meses)

### Hitos Importantes:
- **Mes 1:** Sistema levanta con autenticación funcional
- **Mes 2:** Catálogo de restaurantes visible y gestión de repartidores
- **Mes 3:** MVP completo - flujo de pedido end-to-end funcional
- **Mes 4:** Sistema pulido con funcionalidades avanzadas
- **Mes 5:** Sistema listo para producción

---

## Criterios de Éxito por Etapa

### Criterios Generales (aplican a todas las etapas):
- ✓ Código revisado y aprobado (code review)
- ✓ Tests automatizados escritos y pasando
- ✓ Documentación actualizada
- ✓ Sin errores en lint/formateo
- ✓ CI pipeline verde
- ✓ Demo funcional al stakeholder

### Definición de "Done" para cada etapa:
Una etapa se considera completa cuando:

1. **Funcionalidad:**
   - Todos los entregables listados están implementados
   - Todos los criterios de aceptación se cumplen
   - No hay bugs críticos o bloqueantes

2. **Calidad:**
   - Tests unitarios y de integración pasan al 100%
   - Cobertura de código cumple con el estándar del proyecto
   - Code review completado y aprobado
   - Linting sin errores

3. **Documentación:**
   - README actualizado si aplica
   - API docs generadas (Swagger)
   - Comentarios en código para lógica compleja
   - Diagramas actualizados si hubo cambios arquitectónicos

4. **Integración:**
   - Se integra correctamente con etapas anteriores
   - No rompe funcionalidad existente (regression tests)
   - Docker Compose levanta sin errores
   - Todos los servicios se comunican correctamente

5. **Demo:**
   - Se puede demostrar la funcionalidad en vivo
   - Frontend muestra las nuevas capacidades
   - Stakeholders aprueban los cambios

---

## Gestión del Proceso Incremental

### Reuniones Sugeridas:
- **Planning de Etapa** (inicio): Definir tareas específicas, estimar esfuerzo, asignar responsables
- **Daily Standup** (diario, 15 min): Compartir progreso, identificar bloqueadores
- **Review de Etapa** (fin): Demo de funcionalidad, recoger feedback
- **Retrospectiva** (fin): Qué salió bien, qué mejorar para siguiente etapa

### Herramientas Recomendadas:
- **Control de versiones:** Git + GitHub
- **Gestión de tareas:** GitHub Projects / Trello / Jira
- **CI/CD:** GitHub Actions
- **Comunicación:** Slack / Discord / Teams
- **Documentación:** Markdown en repo + Wiki de GitHub

### Manejo de Cambios:
- Cambios menores: se incorporan en la etapa actual
- Cambios mayores: se añaden al backlog para etapas futuras
- Se mantiene flexibilidad para reordenar etapas según aprendizajes

### Riesgos y Mitigaciones:
| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Problemas de integración entre servicios | Alto | Tests de integración tempranos, contratos de API claros |
| Complejidad de transacciones distribuidas | Alto | Comenzar con casos simples, implementar saga pattern |
| Rendimiento de microservicios | Medio | Monitoreo desde etapas tempranas, optimización iterativa |
| Curva de aprendizaje de tecnologías | Medio | Spikes técnicos, pair programming, documentación |
| Cambios en requerimientos | Bajo | Metodología ágil permite adaptación, backlog priorizado |

---

## Referencias y Documentos Relacionados

- **INCREMENTAL.md:** Flujo de trabajo incremental (branching, PRs, commits)
- **architecture.md:** Arquitectura técnica del sistema
- **use-case.md:** Casos de uso principales
- **README.md:** Guía de inicio rápido y setup

---

## Notas Finales

Este documento es una **guía viviente** que debe actualizarse conforme el proyecto evoluciona. Las etapas pueden ajustarse según:
- Capacidad del equipo
- Prioridades de negocio
- Aprendizajes durante el desarrollo
- Feedback de usuarios/stakeholders

**Principios clave de la metodología incremental aplicada aquí:**
1. **Entregar valor temprano y frecuentemente**
2. **Validar con usuarios/stakeholders continuamente**
3. **Mantener el sistema siempre en estado funcional**
4. **Adaptarse a cambios sin romper lo construido**
5. **Priorizar aprendizaje y mejora continua**

---

**Versión:** 1.0  
**Última actualización:** 2025-11-17  
**Autores:** Equipo Pedidos-Domicilio
