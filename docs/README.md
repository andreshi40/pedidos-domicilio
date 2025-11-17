# Documentación del Proyecto Pedidos-Domicilio

Esta carpeta contiene toda la documentación del proyecto organizada por categorías.

## 📋 Planificación y Metodología

### Etapas de Desarrollo Incremental
- **[ETAPAS_INCREMENTALES.md](./ETAPAS_INCREMENTALES.md)** 📘  
  Documento completo y detallado que define las 7 etapas de desarrollo del proyecto usando metodología incremental. Incluye:
  - Descripción de cada etapa con componentes a implementar
  - Entregables y criterios de aceptación
  - Cronograma sugerido (19-20 semanas)
  - Dependencias entre etapas
  - Hitos importantes
  - Gestión de riesgos

- **[ETAPAS_RESUMEN.md](./ETAPAS_RESUMEN.md)** 📄  
  Vista rápida y condensada de las etapas. Ideal para consulta diaria y seguimiento. Incluye:
  - Tabla resumen de todas las etapas
  - Checklist de entregables clave
  - Backlog priorizado
  - Estimaciones de velocidad de equipo

### Proceso de Trabajo
- **[INCREMENTAL.md](./INCREMENTAL.md)** 🔄  
  Flujo de trabajo incremental del día a día. Define:
  - Estrategia de branching (feature/, fix/, chore/)
  - Guías para Pull Requests
  - Formato de commits
  - Tests y validación
  - Tablero Kanban
  - CI/CD

### Gestión del Proyecto
- **[KANBAN_ISSUES.md](./KANBAN_ISSUES.md)** 📊  
  Uso de issues y tableros para gestión de tareas

- **[GITHUB_KANBAN.md](./GITHUB_KANBAN.md)** 🎯  
  Configuración específica de GitHub Projects para el proyecto

---

## 🏗️ Arquitectura y Diseño Técnico

### Documentación de Arquitectura
- **[architecture.md](./architecture.md)** 🏛️  
  Arquitectura completa del sistema incluyendo:
  - Resumen de microservicios y componentes
  - Stack tecnológico (Python, FastAPI, Flask, PostgreSQL, MongoDB, Redis)
  - Diagrama de arquitectura (Mermaid)
  - Comunicación entre servicios
  - Flujos de datos importantes

### Casos de Uso
- **[use-case.md](./use-case.md)** 📝  
  Caso de uso principal: "Crear pedido y asignar repartidor"
  - Flujo principal (escenario exitoso)
  - Flujos alternos y excepciones
  - Reglas de negocio
  - Endpoints relevantes
  - Criterios de aceptación para tests

---

## 📊 Diagramas Visuales

### Diagramas de Etapas Incrementales
- **[etapas-incrementales.mmd](./etapas-incrementales.mmd)** 📅  
  Diagrama de Gantt mostrando el timeline de desarrollo de las 7 etapas.
  Renderizable en https://mermaid.live o con mermaid-cli

- **[etapas-dependencias.mmd](./etapas-dependencias.mmd)** 🔗  
  Grafo de dependencias entre etapas, mostrando qué etapas requieren otras.

### Diagrama de Arquitectura
- **[architecture.mmd](./architecture.mmd)** 🏗️  
  Diagrama de arquitectura de microservicios en formato Mermaid

- **[architecture-ascii.txt](./architecture-ascii.txt)** 📟  
  Versión ASCII del diagrama de arquitectura para terminales

---

## 🚀 Guías de Inicio Rápido

### Para Nuevos Desarrolladores
1. Lee el **[README principal](../README.md)** para setup inicial
2. Revisa **[ETAPAS_RESUMEN.md](./ETAPAS_RESUMEN.md)** para entender el roadmap
3. Consulta **[INCREMENTAL.md](./INCREMENTAL.md)** para el flujo de trabajo
4. Explora **[architecture.md](./architecture.md)** para entender la arquitectura

### Para Project Managers
1. Consulta **[ETAPAS_INCREMENTALES.md](./ETAPAS_INCREMENTALES.md)** para planificación completa
2. Usa **[ETAPAS_RESUMEN.md](./ETAPAS_RESUMEN.md)** para seguimiento de progreso
3. Revisa **[GITHUB_KANBAN.md](./GITHUB_KANBAN.md)** para gestión de tareas

### Para Arquitectos/Tech Leads
1. Estudia **[architecture.md](./architecture.md)** para visión técnica completa
2. Analiza **[use-case.md](./use-case.md)** para flujos críticos
3. Revisa diagramas `.mmd` para visualización

---

## 📈 Cómo Visualizar los Diagramas Mermaid

### Opción 1: Online (más fácil)
1. Ve a https://mermaid.live
2. Copia el contenido de cualquier archivo `.mmd`
3. Pégalo en el editor
4. Exporta como PNG/SVG si lo necesitas

### Opción 2: Localmente con CLI
```bash
# Instalar mermaid-cli (requiere Node.js)
npm install -g @mermaid-js/mermaid-cli

# Renderizar un diagrama
mmdc -i docs/etapas-incrementales.mmd -o docs/etapas-incrementales.png

# Renderizar todos los diagramas
mmdc -i docs/architecture.mmd -o docs/architecture.svg
mmdc -i docs/etapas-incrementales.mmd -o docs/etapas-incrementales.png
mmdc -i docs/etapas-dependencias.mmd -o docs/etapas-dependencias.png
```

### Opción 3: En GitHub
Los archivos `.mmd` se renderizan automáticamente si los incluyes en Markdown:

```markdown
```mermaid
// contenido del archivo .mmd
```
```

---

## 🗂️ Índice de Todos los Documentos

| Documento | Categoría | Descripción |
|-----------|-----------|-------------|
| [ETAPAS_INCREMENTALES.md](./ETAPAS_INCREMENTALES.md) | Planificación | Etapas de desarrollo completas |
| [ETAPAS_RESUMEN.md](./ETAPAS_RESUMEN.md) | Planificación | Resumen rápido de etapas |
| [INCREMENTAL.md](./INCREMENTAL.md) | Proceso | Flujo de trabajo incremental |
| [KANBAN_ISSUES.md](./KANBAN_ISSUES.md) | Gestión | Uso de issues y tableros |
| [GITHUB_KANBAN.md](./GITHUB_KANBAN.md) | Gestión | GitHub Projects setup |
| [architecture.md](./architecture.md) | Arquitectura | Arquitectura técnica completa |
| [use-case.md](./use-case.md) | Diseño | Caso de uso principal |
| [etapas-incrementales.mmd](./etapas-incrementales.mmd) | Diagrama | Timeline Gantt de etapas |
| [etapas-dependencias.mmd](./etapas-dependencias.mmd) | Diagrama | Grafo de dependencias |
| [architecture.mmd](./architecture.mmd) | Diagrama | Arquitectura de microservicios |
| [architecture-ascii.txt](./architecture-ascii.txt) | Diagrama | Arquitectura en ASCII |

---

## 🔄 Mantenimiento de la Documentación

Esta documentación es **viviente** y debe actualizarse:

### ¿Cuándo actualizar?
- Al completar cada etapa
- Cuando cambie la arquitectura
- Al añadir/modificar servicios
- Cuando se identifiquen riesgos nuevos
- Al final de cada sprint/iteración

### ¿Quién actualiza?
- **Tech Lead:** architecture.md, diagramas técnicos
- **Project Manager:** ETAPAS_INCREMENTALES.md, cronogramas
- **Todo el equipo:** INCREMENTAL.md, READMEs
- **Desarrolladores:** Comentarios en código, API docs

### Checklist de Actualización
- [ ] Fecha actualizada al final del documento
- [ ] Cambios reflejados en diagramas si aplica
- [ ] Links internos funcionando
- [ ] Ortografía y formato revisados
- [ ] Cambios comunicados al equipo

---

## 🤝 Contribuir a la Documentación

Si encuentras errores, inconsistencias o áreas de mejora:

1. Crea un issue describiendo el problema
2. O mejor aún, abre un PR con la corrección
3. Sigue el formato y estilo existente
4. Usa Markdown correctamente
5. Verifica que los enlaces funcionen

---

## 📞 Contacto y Soporte

¿Dudas sobre la documentación?
- Abre un issue en el repositorio
- Contacta al Tech Lead del proyecto
- Pregunta en el canal de Slack/Discord del equipo

---

**Última actualización:** 2025-11-17  
**Mantenido por:** Equipo Pedidos-Domicilio  
**Licencia:** Ver LICENSE en raíz del proyecto
