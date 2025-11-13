# Caso de uso: Crear pedido y asignación de repartidor

## 1. Identificación
- ID: UC-01
- Título: Crear pedido y asignar repartidor
- Actor principal: Cliente (usuario final usando el Frontend)
- Actores secundarios: Frontend (Flask), API Gateway (FastAPI), Servicio Pedidos (FastAPI), Servicio Restaurantes (FastAPI), Servicio Repartidores (FastAPI), Servicio de Autenticación (FastAPI)
- Objetivo: El cliente crea un pedido desde la interfaz; el sistema reserva stock en el restaurante, persiste el pedido y asigna un repartidor disponible (si hay).

## 2. Precondiciones
- El usuario está autenticado (o para flujos públicos, la ruta permite acceso sin token según configuración de `PUBLIC_ROUTES`).
- El restaurante y los ítems solicitados existen en el catálogo.
- Las bases de datos y servicios (restaurantes, repartidores, pedidos) están operativos.

## 3. Postcondiciones
- En caso exitoso: se crea un registro de pedido en `pedidos-db` con estado `asignado` y snapshot del repartidor; las unidades pedidas en `restaurantes-db` han sido reservadas (reducción de stock).
- En caso sin repartidor disponible: pedido creado con estado `creado`; el background assigner reintentará la asignación posteriormente.
- En caso de fallo durante reservas: no se crea el pedido (o se revierte la reserva previa) y se devuelve un error al cliente.

## 4. Flujo principal (escenario exitoso)
1. Cliente llena el formulario de pedido y envía (Front-End → Gateway):
   - Endpoint (cliente → gateway): POST /api/v1/pedidos
   - Payload (ejemplo):
     ```json
     {
       "restaurante_id": "rest2",
       "cliente_email": "juan@example.com",
       "direccion": "Calle Falsa 123",
       "items": [{"item_id": "s1", "cantidad": 2}]
     }
     ```
2. Gateway valida token (si aplica) y reenvía la petición a `pedidos-service` (forward).
3. `pedidos-service` valida stock del restaurante leyendo `/api/v1/restaurantes/{rid}/menu` (GET) y construye un mapa de disponibilidad.
4. `pedidos-service` hace llamadas a `restaurantes-service` para reservar cada ítem:
   - POST /api/v1/restaurantes/{rid}/menu/{item}/reserve?cantidad=2
   - Si alguna reserva falla, el servicio libera reservas previas y responde error al cliente.
5. Si reservas OK, `pedidos-service` persiste el pedido en `pedidos-db` con estado `creado` (o momentáneamente) y guarda los `OrderItem` relacionados.
6. `pedidos-service` intenta asignar un repartidor inmediatamente llamando a `repartidores-service`:
   - POST http://repartidores-service:8004/api/v1/repartidores/assign-next
   - Caso 200: el servicio `repartidores` devuelve JSON con el repartidor asignado; `pedidos` actualiza la orden: estado `asignado`, guarda snapshot (id, nombre, telefono) en la orden.
   - Caso 204: no hay repartidores disponibles; el pedido permanece en estado `creado`.
7. `pedidos-service` devuelve al frontend el detalle de la orden (id, items, estado, repartidor si aplica). Frontend muestra confirmación al usuario.

## 5. Flujos alternos y excepciones
A1 — Item no existe en menú
- Cuando `pedidos-service` detecta que `item_id` no está en el menú: devuelve 400 Bad Request con detalle "Item X no encontrado en el restaurante". Ninguna reserva ni persistencia ocurre.

A2 — Stock insuficiente
- Si la verificación o la llamada a `reserve` devuelven error por falta de stock: `pedidos-service` hace rollback de reservas ya hechas (llamando a `/release`) y devuelve 400 con detalle "Stock insuficiente".

A3 — Repartidores no disponibles (inmediato)
- Si `repartidores/assign-next` responde 204 (sin contenido): el pedido queda con estado `creado`. El `pedidos-service` background assigner intentará asignarlo periódicamente.

A4 — Error de comunicación entre servicios
- Si una llamada HTTP entre servicios falla (timeout o 5xx), `pedidos-service` intentará rollback de reservas y responderá 500 Internal Server Error con un mensaje indicando fallo de subsistema.

A5 — Falla durante persistencia de pedido
- Si fallara el commit a la base de datos luego de reservar, `pedidos-service` intentará liberar las reservas y responderá 500.

## 6. Reglas de negocio / decisiones importantes
- La asignación de repartidor se debe realizar de forma atómica desde el servicio `repartidores` usando SQL con bloqueo (ej.: `SELECT ... FOR UPDATE SKIP LOCKED`) para evitar asignar un mismo repartidor a dos pedidos.
- Las reservas en `restaurantes` deben compensarse (release) si cualquier paso posterior falla.
- `pedidos-service` posee un background assigner que reintenta asignaciones para pedidos en estado `creado` cada N segundos.

## 7. Endpoints relevantes (resumen)
- Frontend → Gateway:
  - POST /api/v1/pedidos  (crea pedido)
  - GET /api/v1/pedidos/{order_id} (consultar estado)
- Pedidos → Restaurantes:
  - GET /api/v1/restaurantes/{rid}/menu
  - POST /api/v1/restaurantes/{rid}/menu/{item}/reserve?cantidad={n}
  - POST /api/v1/restaurantes/{rid}/menu/{item}/release?cantidad={n}
- Pedidos → Repartidores:
  - POST /api/v1/repartidores/assign-next
- Gateway → Auth (cuando aplica):
  - POST /login, POST /register, GET /me

## 8. Datos de ejemplo (respuestas esperadas)
- Respuesta exitosa de creación de pedido (200):
  ```json
  {
    "id": "e42bbdeb-7b79-46de-849b-df6a6ad3d9b8",
    "restaurante_id": "rest2",
    "cliente_email": "juan@example.com",
    "direccion": "Calle Falsa 123",
    "items": [{"item_id":"s1","nombre":"Sushi Mix","precio":12.0,"cantidad":2}],
    "estado": "asignado",
    "repartidor": {"id":"rt_01","nombre":"Luis","telefono":"300111222"}
  }
  ```

- Respuesta cuando no hay repartidor disponible (204 from assign-next → final payload):
  - Pedido creado con `estado: "creado"` y `repartidor: null`.

## 9. Criterios de aceptación (tests)
- TA1 (happy path): Crear pedido con items en stock y un repartidor disponible → 200, estado `asignado`, stock decrementado.
- TA2 (sin repartidor): Crear pedido cuando no hay repartidores disponibles → 200, estado `creado`; background assigner debe asignar cuando un repartidor se vuelva `disponible`.
- TA3 (sin stock): Crear pedido con cantidad mayor a stock → 400 y no se persiste el pedido; stock sin cambios.
- TA4 (reserva parcial falla): Si reservar item A pasa pero item B falla, el sistema libera A y devuelve 400.

## 10. Casos de prueba sencillos (pasos)
- Prueba 1 (happy path):
  1. Asegurar que `restaurantes` tenga item s1 con cantidad >=2.
  2. Asegurar que existe un repartidor con estado `disponible`.
  3. POST /api/v1/pedidos con payload (ver más arriba).
  4. Verificar respuesta 200 con `estado: "asignado"` y que `repartidor` documento está presente.
  5. Verificar en `restaurantes-db` que stock se redujo en 2.

- Prueba 2 (no repartidor disponible):
  1. Marcar todos los repartidores como `ocupado` (o eliminar disponibles).
  2. POST /api/v1/pedidos.
  3. Verificar respuesta con `estado: "creado"`.
  4. Cambiar un repartidor a `disponible` y esperar el próximo tick del background assigner; verificar que el pedido pase a `asignado`.

## 11. Notas de implementación y consideraciones técnicas
- Tiempos de timeout entre servicios deben ser modestos (2-3s) y el servicio debe fallar de manera predecible si un downstream no responde.
- Para evitar inconsistencias, cualquier reserva en `restaurantes` debe ser compensada con llamadas a `/release` si la transacción global no puede completarse.
- El endpoint `assign-next` en `repartidores` debe ser idempotente y seguro bajo concurrencia.

---
Documento generado para servir como base de historias de usuario, pruebas de integración y documentación técnica.
