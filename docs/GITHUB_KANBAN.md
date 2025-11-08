# Tablero Kanban (fallback en repo)

Este archivo representa un tablero Kanban ligero dentro del repo, creado como alternativa cuando la creación automática de un Project en GitHub no está disponible.

Columnas:

- Backlog
- Ready
- In Progress
- Review
- Done

Tareas sugeridas (puedes crear Issues desde estas líneas si habilitas Issues en el repo):

## Backlog

- Agregar plantillas de PR/Issue (`.github/PULL_REQUEST_TEMPLATE.md`, `.github/ISSUE_TEMPLATE.md`).
- Crear `CHANGELOG.md` y definir formato de entries.
- Mejorar CI: añadir caching, matrix y reporting de cobertura.

## Ready

- Revisar formularios y botones (`.full-width`) para evitar roturas de UX.
- Añadir favicon y ajustes pequeños de branding.

## In Progress

- Implementar tablero Kanban en GitHub (si se habilitan Issues/Projects) — tarea automática pendiente.

## Review

- Revisar tests E2E y flujos de autenticación (autologin / refresh tokens).

## Done

- Definir perfiles de inicio de sesión (cliente/restaurante/repartidor/admin).

---

Cómo usar:

1. Si habilitas Issues en GitHub, puedes crear Issues desde las entradas y moverlas al tablero.
2. Si prefieres que yo cree el Project en GitHub, habilita Issues/Projects o dame permisos y lo intento de nuevo.

Notas:

- Este archivo se agregó porque la API REST devolvió 404 al intentar crear un Project de repositorio (fallo de permisos o endpoint restringido). Mantener `docs/KANBAN_ISSUES.md` y este archivo sincronizados facilita la migración manual.
