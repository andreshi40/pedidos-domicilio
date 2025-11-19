# Pedidos Domicilio

Bienvenido a la documentación del proyecto Pedidos Domicilio.

Este sitio reúne la información clave sobre la arquitectura, metodología incremental y las etapas de desarrollo del sistema.

## Resumen del Proyecto

Plataforma de pedidos a domicilio construida con una arquitectura de **microservicios** (FastAPI) y un **frontend Flask**. Incluye autenticación multi-rol (cliente, restaurante, repartidor), gestión de menús, pedidos con reserva atómica de stock y asignación automática de repartidores.

## Páginas Clave

- **Flujo Incremental**: Cómo trabajamos día a día (`INCREMENTAL.md`).
- **Etapas Incrementales**: Entregables y progreso por fase (`ETAPAS_INCREMENTALES.md`).
- **Estado del Arte**: Justificación tecnológica y alineación con prácticas modernas (`estado-del-arte.md`).
- **Arquitectura**: Diagrama y componentes (`architecture.md`, `architecture.mmd`, `architecture-ascii.txt`).
- **Caso de Uso**: Flujo detallado de creación de pedidos (`use-case.md`).

## Tecnologías Principales

- Backend: FastAPI, MongoDB, PostgreSQL, Redis, JWT, SQLAlchemy
- Frontend: Flask + Jinja2, HTML/CSS/JS
- Infraestructura: Docker & Docker Compose, control de versiones con Git/GitHub

## Cómo Ejecutar la Documentación Localmente

1. Instala dependencias (en tu entorno virtual):
   ```bash
   pip install mkdocs mkdocs-material
   ```
2. Inicia el servidor de documentación:
   ```bash
   mkdocs serve
   ```
3. Abre en el navegador:
   ```bash
   http://127.0.0.1:8000
   ```

## Próximos Pasos (Docs)

- Añadir secciones de Testing y CI/CD.
- Incorporar ejemplos de API (OpenAPI / curl).
- Agregar página de métricas y monitoreo futuro.

---
_Última actualización: Noviembre 2025_.
