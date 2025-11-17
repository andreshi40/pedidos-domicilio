# Etapas Incrementales del Proyecto - Pedidos a Domicilio

## Metodología Aplicada

Este proyecto siguió una **metodología de desarrollo incremental**, donde cada incremento agrega funcionalidad completa y verificable al sistema. Cada etapa produce un entregable funcional que puede ser desplegado y probado independientemente.

---

## ETAPA 1: Infraestructura Base y Arquitectura de Microservicios

### Objetivo
Establecer la infraestructura básica del proyecto con contenedores Docker y la arquitectura de microservicios.

### Actividades Realizadas
1. **Configuración del entorno de desarrollo**
   - Creación del repositorio Git
   - Configuración de `.env` para variables de entorno
   - Setup de Docker Compose con orquestación de servicios

2. **Implementación de servicios base**
   - Frontend (Flask) - Puerto 5000
   - API Gateway (FastAPI) - Puerto 8000
   - Servicio de Autenticación (FastAPI + MongoDB) - Puerto 8001
   - Servicio de Restaurantes (FastAPI + PostgreSQL) - Puerto 8002
   - Servicio de Pedidos (FastAPI + PostgreSQL + Redis) - Puerto 8003
   - Servicio de Repartidores (FastAPI + PostgreSQL) - Puerto 8004

3. **Configuración de bases de datos**
   - MongoDB para autenticación (`auth_db`)
   - PostgreSQL para restaurantes (`service1_db`)
   - PostgreSQL para pedidos (`pedidos_db`)
   - PostgreSQL para repartidores (`repartidores_db`)
   - Redis para caché y coordinación

### Entregables
- ✅ Docker Compose funcional con todos los servicios
- ✅ Servicios levantados y comunicándose entre sí
- ✅ Health checks implementados en cada servicio
- ✅ Documentación de arquitectura (architecture.md, architecture.mmd)

### Criterios de Aceptación
- Todos los contenedores inician correctamente
- Los servicios responden a sus endpoints `/health`
- Las bases de datos están accesibles desde sus respectivos servicios

---

## ETAPA 2: Sistema de Autenticación y Gestión de Usuarios

### Objetivo
Implementar un sistema robusto de autenticación con JWT y gestión de múltiples roles de usuario.

### Actividades Realizadas
1. **Servicio de Autenticación**
   - Registro de usuarios con bcrypt para passwords
   - Login con generación de tokens JWT
   - Validación de tokens en API Gateway
   - Endpoints: `/register`, `/login`, `/me`

2. **Gestión de roles**
   - Cliente: usuario que hace pedidos
   - Restaurante: propietario de restaurante
   - Repartidor: conductor de entregas

3. **Integración con API Gateway**
   - Middleware de validación JWT
   - Inyección de headers `X-User-Id` y `X-User-Email`
   - Rutas públicas vs. rutas protegidas
   - Configuración de `PUBLIC_ROUTES`

### Entregables
- ✅ Sistema de registro/login funcional
- ✅ Tokens JWT con tiempo de expiración
- ✅ Validación centralizada en API Gateway
- ✅ Sesiones persistentes en el frontend

### Criterios de Aceptación
- Los usuarios pueden registrarse con email y contraseña
- El login genera un token JWT válido
- Las rutas protegidas rechazan peticiones sin token
- Los roles se respetan en el acceso a funcionalidades

---

## ETAPA 3: Catálogo de Restaurantes y Menús

### Objetivo
Crear el sistema de gestión de restaurantes con sus menús y control de inventario.

### Actividades Realizadas
1. **CRUD de Restaurantes**
   - Crear restaurante (asociado a user_id)
   - Listar restaurantes con búsqueda por nombre
   - Ver detalles de restaurante individual
   - Actualizar información del restaurante
   - Upload de logos/fotos de restaurantes

2. **Gestión de Menús**
   - Agregar items al menú (nombre, precio, cantidad)
   - Listar menú por restaurante
   - Eliminar items del menú
   - Control de stock en tiempo real

3. **Almacenamiento persistente**
   - Volumen Docker para fotos de restaurantes
   - Endpoint `/restaurante/photo/{rest_id}` para servir imágenes
   - Validación de formatos de imagen

4. **Seeding inicial**
   - 3 restaurantes de ejemplo (La Pizzeria, Sushi Express, Taco House)
   - Items de menú con precios y cantidades iniciales

### Entregables
- ✅ API REST completa para restaurantes
- ✅ Sistema de carga y visualización de imágenes
- ✅ Dashboard de restaurante con gestión de menú
- ✅ Búsqueda de restaurantes por nombre

### Criterios de Aceptación
- Los restaurantes se crean vinculados al user_id del propietario
- El stock se actualiza al reservar/liberar items
- Las fotos se persisten entre reinicios del contenedor
- La búsqueda filtra correctamente por nombre

---

## ETAPA 4: Sistema de Pedidos con Reserva de Stock

### Objetivo
Implementar el flujo completo de creación de pedidos con reserva atómica de stock.

### Actividades Realizadas
1. **Creación de pedidos**
   - Endpoint `POST /api/v1/pedidos`
   - Validación de stock disponible
   - Reserva atómica de items usando `SELECT FOR UPDATE`
   - Persistencia de pedido con items

2. **Gestión de estado del pedido**
   - Estados: `creado`, `asignado`, `completado`
   - Transiciones controladas de estado
   - Snapshot de información del pedido

3. **Rollback de transacciones**
   - Release de items si falla alguna reserva
   - Manejo de errores parciales
   - Endpoint `/release` para devolver stock

4. **Consulta de pedidos**
   - Ver estado de pedido individual
   - Listar pedidos por restaurante con filtros (mes/año)
   - Estadísticas de ventas por día y por mes
   - Dashboard de restaurante con métricas

5. **Información del cliente**
   - Captura de nombre, apellido, teléfono
   - Dirección de entrega
   - Email del cliente

### Entregables
- ✅ API de pedidos con transacciones ACID
- ✅ Sistema de reserva/liberación de stock
- ✅ Endpoint de estadísticas para restaurantes
- ✅ Vista de confirmación de pedido para clientes

### Criterios de Aceptación
- No se sobrevende stock (race conditions controladas)
- Si falla una reserva, se revierten las anteriores
- Los pedidos persisten correctamente en la base de datos
- Las estadísticas reflejan datos en tiempo real

---

## ETAPA 5: Sistema de Repartidores y Asignación Automática

### Objetivo
Implementar la gestión de repartidores y asignación atómica de pedidos.

### Actividades Realizadas
1. **CRUD de Repartidores**
   - Registro de repartidores (disponible por defecto)
   - Estados: `disponible`, `ocupado`
   - Upload de foto de perfil
   - Información: nombre, teléfono, estado

2. **Asignación atómica**
   - Endpoint `POST /api/v1/repartidores/assign-next`
   - Query con `SELECT FOR UPDATE SKIP LOCKED`
   - Prevención de race conditions
   - Respuesta 200 (asignado) o 204 (sin disponibles)

3. **Liberación de repartidores**
   - Endpoint `POST /api/v1/repartidores/{id}/free`
   - Cambio de estado a `disponible`
   - Integración con completado de pedidos

4. **Background Assigner**
   - Thread que escanea pedidos en estado `creado`
   - Reintenta asignación cada 5 segundos
   - Manejo de fallos sin bloquear el servicio

5. **Dashboard de repartidor**
   - Vista de pedido actual asignado
   - Histórico de pedidos completados
   - Cálculo de ganancias (10% del total del pedido)
   - Botón para completar pedido

### Entregables
- ✅ API de repartidores con asignación atómica
- ✅ Sistema de liberación automática al completar pedido
- ✅ Background assigner para pedidos sin repartidor
- ✅ Dashboard funcional para repartidores

### Criterios de Aceptación
- Un repartidor solo puede tener un pedido asignado a la vez
- La asignación es atómica (sin doble asignación)
- Los repartidores se liberan automáticamente al completar
- El background assigner funciona sin intervención manual

---

## ETAPA 6: Frontend y Experiencia de Usuario

### Objetivo
Crear una interfaz web completa y amigable para todos los tipos de usuario.

### Actividades Realizadas
1. **Página de inicio pública**
   - Hero section con logo de la aplicación
   - Búsqueda de restaurantes por nombre
   - Grid de restaurantes con fotos y ratings
   - Enlaces a registro de usuarios

2. **Sistema de navegación**
   - Menú responsive con toggle para móviles
   - Dropdown para crear usuarios (Cliente/Restaurante/Repartidor)
   - Indicador de sesión activa
   - Logout funcional

3. **Dashboard de Restaurante**
   - Estadísticas del mes (4 cards): Ventas, Total Pedidos, Pendientes, Completados
   - Visualización del logo del restaurante
   - Tabla de menú con opciones de editar/eliminar
   - Formulario para agregar items al menú
   - Tabla de ventas por día
   - Lista de todos los pedidos del mes con detalles
   - Upload de logo del restaurante

4. **Dashboard de Cliente**
   - Búsqueda de restaurantes
   - Vista de menú del restaurante
   - Carrito de compras
   - Formulario de pedido con datos de entrega
   - Página de confirmación con seguimiento en tiempo real

5. **Dashboard de Repartidor**
   - Información del pedido asignado
   - Datos del cliente y dirección
   - Items del pedido
   - Botón para completar entrega
   - Histórico de entregas y ganancias

6. **Seguimiento de pedido en tiempo real**
   - Polling cada 5 segundos
   - Actualización automática de estado
   - Información del repartidor asignado
   - Foto del repartidor
   - Estado dinámico: "En camino" → "Pedido entregado"

### Entregables
- ✅ Frontend completo con Flask + Jinja2
- ✅ CSS responsive con diseño moderno
- ✅ Dashboards específicos por rol
- ✅ Seguimiento en tiempo real de pedidos

### Criterios de Aceptación
- La interfaz es intuitiva y fácil de usar
- El diseño es responsive (mobile-friendly)
- Las actualizaciones en tiempo real funcionan correctamente
- Todos los roles tienen acceso a sus funcionalidades

---

## ETAPA 7: Branding y Mejoras de UI/UX

### Objetivo
Implementar la identidad visual de la aplicación y mejorar la experiencia del usuario.

### Actividades Realizadas
1. **Diseño e implementación del logo**
   - Creación de `deliapp-logo.svg`
   - Paleta de colores: #E85C3F (naranja)
   - Iconografía: caja de entrega + persona
   - Tipografía: Arial bold para "deliapp"

2. **Integración del logo**
   - Header: logo 32px + título de página
   - Hero de homepage: logo 64px
   - Footer: logo 24px + copyright
   - Favicon (opcional)

3. **Reorganización de layouts**
   - Dashboard de restaurante: estadísticas arriba, menú en medio, pedidos abajo
   - Grid de 2 columnas para restaurantes
   - Cards con gradientes para métricas
   - Badges de estado con colores semánticos

4. **Mejoras de usabilidad**
   - Placeholder de búsqueda: "Buscar por nombre de restaurante"
   - Eliminación de enlaces duplicados en menú
   - Estados visuales claros (completado=verde, en camino=naranja, pendiente=rojo)
   - Prevención de doble submit en formularios

5. **Optimizaciones de rendimiento**
   - Llamadas directas a servicios (bypass gateway para imágenes)
   - Caché de fotos con query params aleatorios
   - Lazy loading de imágenes con fallback a emoji

### Entregables
- ✅ Logo SVG profesional e identidad visual
- ✅ UI modernizada con mejores colores y espaciado
- ✅ Experiencia de usuario mejorada
- ✅ Diseño consistente en toda la aplicación

### Criterios de Aceptación
- El logo aparece consistentemente en todas las páginas
- Los colores siguen una paleta coherente
- La navegación es intuitiva sin elementos duplicados
- El diseño es profesional y atractivo

---

## ETAPA 8: Bug Fixes y Estabilización

### Objetivo
Corregir errores críticos y mejorar la estabilidad del sistema.

### Actividades Realizadas
1. **Corrección de errores de template**
   - Fix: `order['items']` en lugar de `order.items` (Jinja2)
   - Fix: URLs duplicadas en llamadas HTTP
   - Fix: Manejo de campos opcionales (foto_url, rating)

2. **Corrección de lógica de negocio**
   - Fix: Repartidor no se liberaba al completar pedido (URL path duplicado)
   - Fix: Endpoint `/api/v1/restaurante/{id}/orders` no estaba en gateway
   - Fix: Llamada directa a pedidos-service desde frontend

3. **Mejoras de robustez**
   - Logging para debugging (`print(flush=True)`)
   - Manejo de excepciones sin fallar completamente
   - Timeouts en requests HTTP
   - Validación de stock antes de reservar

4. **Correcciones de estado**
   - Nuevos repartidores creados con `estado='disponible'`
   - Liberación automática al completar pedido
   - Estado dinámico en vista de cliente

5. **Persistencia de datos**
   - Volumen Docker para fotos de restaurantes
   - Prevención de pérdida de imágenes en rebuild
   - Índice en `user_id` para queries eficientes

### Entregables
- ✅ Bugs críticos corregidos
- ✅ Sistema estable y confiable
- ✅ Logs para debugging
- ✅ Manejo robusto de errores

### Criterios de Aceptación
- No hay errores 500 en operaciones normales
- Los repartidores se liberan correctamente
- Las imágenes persisten entre reinicios
- El estado del pedido se actualiza correctamente

---

## ETAPA 9: Documentación y Control de Versiones

### Objetivo
Documentar el proyecto y mantener un historial claro de cambios.

### Actividades Realizadas
1. **Documentación técnica**
   - `architecture.md`: Diagrama y explicación de arquitectura
   - `architecture.mmd`: Diagrama Mermaid de flujos
   - `use-case.md`: Caso de uso detallado de creación de pedidos
   - `INCREMENTAL.md`: Guía de flujo de trabajo incremental

2. **Documentación de usuario**
   - `README.md`: Instrucciones de instalación y ejecución
   - Comentarios en código para endpoints complejos
   - Ejemplos de payloads y respuestas

3. **Control de versiones**
   - Commits atómicos con mensajes descriptivos
   - Formato: `tipo(scope): mensaje`
   - Ejemplo: `feat(frontend): agregar logo`
   - Push al repositorio remoto (GitHub)

4. **Gestión de cambios**
   - Commit incremental de features
   - Agrupación lógica de cambios relacionados
   - Historial limpio y comprensible

### Entregables
- ✅ Documentación completa del proyecto
- ✅ Diagramas de arquitectura
- ✅ Casos de uso documentados
- ✅ Repositorio Git organizado

### Criterios de Aceptación
- La documentación es clara y comprensible
- Los diagramas reflejan la arquitectura real
- El historial de Git es legible
- Los nuevos desarrolladores pueden entender el proyecto

---

## ETAPA 10: Testing y Validación en Producción

### Objetivo
Validar el sistema completo con datos reales y escenarios de uso.

### Actividades Realizadas
1. **Limpieza de datos de prueba**
   - Eliminación de repartidores de testing
   - Mantención de un solo repartidor (Juan Domínguez)
   - Eliminación de pedidos pendientes/asignados
   - Reset de credenciales conocidas

2. **Pruebas de flujo completo**
   - Registro de usuario → Login → Búsqueda → Pedido → Asignación → Entrega
   - Validación de cada rol (Cliente, Restaurante, Repartidor)
   - Pruebas de concurrencia en asignación de repartidores

3. **Validación de características**
   - Stock se decrementa correctamente
   - Repartidores se asignan atómicamente
   - Dashboard muestra datos en tiempo real
   - Fotos se cargan correctamente

4. **Pruebas de resiliencia**
   - Reinicio de contenedores sin pérdida de datos
   - Manejo de servicios caídos
   - Recuperación de errores parciales

5. **Credenciales de testing**
   - Repartidor: velocito2025@gmail.com / juan123456
   - Restaurante Adams Burguer: restaurante.test@gmail.com / test123456
   - Restaurante La Pizzeria: pizzeria.italia@gmail.com / pizza2024
   - Restaurante Sushi Express: sushi.express@gmail.com / sushi2024
   - Restaurante Taco House: taco.house@gmail.com / tacos123
   - Restaurante Sabor Cubano: sabor.cubano@gmail.com / habana123

### Entregables
- ✅ Sistema validado end-to-end
- ✅ Datos de prueba limpios y consistentes
- ✅ Credenciales documentadas
- ✅ Sistema listo para demostración

### Criterios de Aceptación
- El flujo completo funciona sin errores
- Los datos persisten correctamente
- El sistema maneja múltiples usuarios concurrentes
- No hay memory leaks ni problemas de performance

---

## Resumen de Tecnologías Utilizadas

### Backend
- **FastAPI**: Framework para microservicios (4 servicios)
- **Flask**: Framework para frontend web
- **SQLAlchemy**: ORM para PostgreSQL
- **PyMongo**: Cliente para MongoDB
- **Redis**: Caché y coordinación
- **JWT (python-jose)**: Autenticación con tokens
- **bcrypt**: Hashing de contraseñas
- **Pydantic**: Validación de datos

### Frontend
- **Jinja2**: Motor de templates
- **HTML5/CSS3**: Estructura y estilos
- **JavaScript (Vanilla)**: Interactividad y polling
- **SVG**: Logo vectorial escalable

### Bases de Datos
- **PostgreSQL**: 3 bases de datos (restaurantes, pedidos, repartidores)
- **MongoDB**: Base de datos para autenticación
- **Redis**: Caché y coordinación de pedidos

### DevOps
- **Docker**: Contenedorización de servicios
- **Docker Compose**: Orquestación de contenedores
- **Git**: Control de versiones
- **GitHub**: Repositorio remoto

---

## Métricas del Proyecto

### Líneas de Código (aproximado)
- Backend (Python): ~3,500 líneas
- Frontend (Flask + Templates): ~2,000 líneas
- Configuración (Docker, YAML): ~300 líneas
- Documentación: ~1,500 líneas

### Estructura de Archivos
- 4 microservicios independientes
- 1 API Gateway
- 1 Frontend web
- 5 bases de datos
- 15+ templates HTML
- 8+ archivos de documentación

### Funcionalidades Implementadas
- ✅ Sistema de autenticación multi-rol
- ✅ CRUD completo de restaurantes, menús, repartidores
- ✅ Sistema de pedidos con transacciones ACID
- ✅ Asignación atómica de repartidores
- ✅ Dashboards específicos por rol
- ✅ Seguimiento en tiempo real de pedidos
- ✅ Gestión de stock con reservas/liberaciones
- ✅ Upload y serving de imágenes
- ✅ Estadísticas y métricas de ventas
- ✅ Sistema de búsqueda de restaurantes

---

## Lecciones Aprendidas

### Arquitectura
- La separación en microservicios permite escalabilidad independiente
- El API Gateway centraliza la autenticación y simplifica el frontend
- Cada servicio con su propia base de datos evita acoplamiento

### Desarrollo Incremental
- Entregas pequeñas y frecuentes reducen riesgos
- Cada incremento debe ser funcional y desplegable
- La validación temprana previene errores costosos

### Gestión de Estado
- Las transacciones atómicas son críticas para consistencia
- `SELECT FOR UPDATE SKIP LOCKED` previene race conditions
- El estado debe sincronizarse entre servicios cuidadosamente

### UI/UX
- El polling simple funciona bien para tiempo real básico
- La retroalimentación visual inmediata mejora la experiencia
- Un diseño consistente genera confianza en el usuario

### Testing y Debugging
- Los logs estructurados facilitan el debugging
- Mantener datos de prueba consistentes ahorra tiempo
- Las pruebas manuales end-to-end detectan problemas de integración

---

## Próximos Pasos (Backlog Futuro)

### Mejoras Técnicas
- [ ] WebSockets para tiempo real verdadero
- [ ] Tests automatizados (pytest)
- [ ] CI/CD con GitHub Actions
- [ ] Métricas y monitoring (Prometheus + Grafana)
- [ ] Logging centralizado (ELK stack)

### Nuevas Funcionalidades
- [ ] Sistema de calificaciones y reviews
- [ ] Chat entre cliente y repartidor
- [ ] Notificaciones push
- [ ] Historial de pedidos para clientes
- [ ] Panel de administración global
- [ ] Cupones y descuentos
- [ ] Múltiples direcciones por cliente
- [ ] Tracking GPS del repartidor

### Optimizaciones
- [ ] Caché de menús en Redis
- [ ] Compresión de imágenes automática
- [ ] Paginación en listados grandes
- [ ] Índices adicionales en bases de datos
- [ ] Rate limiting en API Gateway

---

## Conclusión

Este proyecto demostró exitosamente la implementación de una arquitectura de microservicios completa utilizando **metodología incremental**. Cada etapa construyó sobre la anterior, entregando valor funcional en cada iteración.

El enfoque incremental permitió:
- 🎯 Validación temprana de decisiones arquitectónicas
- 🚀 Despliegues frecuentes y funcionales
- 🔄 Flexibilidad para ajustar prioridades
- 📈 Progreso visible y medible
- 🐛 Detección temprana de bugs

El resultado es un sistema robusto, escalable y mantenible que sirve como base sólida para futuras expansiones.

---

**Fecha de Documentación**: Noviembre 17, 2025  
**Versión del Proyecto**: 1.0  
**Autor**: Equipo de Desarrollo Pedidos Domicilio  
**Repositorio**: github.com/andreshi40/pedidos-domicilio
