# Flujo incremental (INCREMENTAL)

Este documento describe el flujo de trabajo incremental recomendado para el proyecto "pedidos-domicilio".
Está pensado para equipos pequeños o individuales que prefieren entregas frecuentes y poco overhead.

Objetivo
-------
- Entregar cambios pequeños, verificables y reversibles.
- Mantener calidad con tests y revisiones rápidas.

Reglas principales
------------------
- Branching:
  - Usa `feature/<descripcion-corta>` para nuevas funcionalidades.
  - Usa `fix/<issue-id>-<descripcion>` para correcciones.
  - Usa `chore/<descripcion>` para tareas de mantenimiento.

- Pull Requests (PR):
  - Cada PR debe ser pequeño y atómico (ideal < 300 líneas).
  - Incluir descripción: Qué cambia, por qué, cómo probarlo y criterios de aceptación.
  - Enlazar la PR a una issue o card del tablero si aplica.
  - Ejecutar CI y esperar resultados antes de merge.

- Commits:
  - Mensajes claros y atómicos.
  - Sigue el formato: `tipo(scope): mensaje` (ej. `feat(frontend): agregar logo`).

- Tests y validación:
  - Ejecuta los tests localmente antes de abrir PR (usa el venv del proyecto).
  - CI ejecutará pytest en pushes/PRs.

- Revisión y merge:
  - Preferir merges por PRs después de code review y CI verde.
  - Mantén PRs pequeños para revisiones rápidas.

Buenas prácticas y recomendaciones
--------------------------------
- Forzar despliegues locales con Docker Compose antes del merge si el cambio toca infraestructura o contenedores.
- No mezcles cambios conceptuales diferentes en una misma PR.
- Mantén un CHANGELOG.md con entradas para releases importantes.

Tablero y visibilidad
---------------------
- Usa un tablero Kanban ligero (GitHub Projects, Trello):
  - Columnas sugeridas: Backlog / Ready / In Progress / Review / Done
  - Limita WIP a 2–3 items por contribuidor.

Plantillas y automatización
---------------------------
- Añade plantillas de PR/Issue para uniformar la información requerida.
- Configura CI (workflow básico ya incluido) que ejecute tests en pushes/PRs.

Ejemplo rápido — checklist al abrir PR
-------------------------------------
1. [ ] Los tests locales pasan (`venv/bin/python -m pytest`).
2. [ ] La PR contiene descripción clara y pasos para reproducir.
3. [ ] Enlace a issue o card si aplica.
4. [ ] El PR tiene máximo 300 líneas de diff si es posible.

Notas finales
-------------
Este flujo es intencionalmente ligero. Si el equipo crece o necesitas más gobernanza, puedes añadir prácticas de Scrum (sprints, planning, retros) sobre esta base incremental.
