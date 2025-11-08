# Tareas (para crear en el tablero Kanban)

Lista de tareas sugeridas para el tablero Kanban (cada entrada puede convertirse en una Issue):

1. Agregar plantillas de PR/Issue
   - Crear `.github/PULL_REQUEST_TEMPLATE.md` y `.github/ISSUE_TEMPLATE.md` (ya creadas en este commit).

2. Revisar otros formularios globales
   - Verificar que el cambio de estilos de `button` no rompa formularios en otras plantillas; añadir `.full-width` donde sea necesario.

3. Documentar cambio rápido
   - Añadir nota breve en `README.md` o comentarios CSS explicando la convención de botones y `.full-width`.

4. Continuar con pendientes mayores
   - Planificar migraciones, seeds y tests E2E.

5. Opcional: Crear tablero Kanban ligero
   - Crear GitHub Project (Board) con columnas Backlog/Ready/In Progress/Review/Done.

6. Mejorar CI
   - Ampliar workflow de CI para caches, matrix y reporting de cobertura.

7. Add CHANGELOG
   - Crear `CHANGELOG.md` y registrar cambios importantes desde la rama `backup/changes-...`.

8. Seguridad: MFA para Admin
   - Explorar e implementar MFA para roles admin (documentar pasos y requisitos).

---

Cómo convertir estas líneas a issues (si habilitas Issues):

```bash
# ejemplo: crear issue para "Revisar otros formularios globales"
gh issue create --title "Revisar otros formularios globales" --body "Verificar que el cambio de estilos de button no rompa formularios y añadir .full-width cuando haga falta." --label "task"
```
