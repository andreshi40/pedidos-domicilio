# Plantilla del Proyecto del Seminario

| Código | Nombre | Correo |
|:---|:---|:---|
| 542378923 | Fulanito de Tal | fulanito.tal@miuniremington.edu.co |
| 542378923 | Fulanito de Tal | fulanito.tal@miuniremington.edu.co |

---

## Objetivos del Seminario

* Diseñar microservicios independientes que se comunican entre sí.
* Implementar API RESTful con FastAPI.
* Utilizar diferentes tipos de bases de datos para cada microservicio.
* Implementar un front-end básico para hacer uso de los microservicios.
* Contenerizar aplicaciones con Docker.
* Orquestar la infraestructura con Docker Compose.

## Documentación del Proyecto

### 📋 Planificación y Metodología
Este proyecto sigue una **metodología incremental** de desarrollo. Consulta los siguientes documentos para entender el proceso:

- **[Etapas Incrementales (Completo)](./docs/ETAPAS_INCREMENTALES.md)** - Definición detallada de las 7 etapas de desarrollo con entregables, criterios de aceptación y cronograma.
- **[Etapas Incrementales (Resumen)](./docs/ETAPAS_RESUMEN.md)** - Vista rápida y checklist de las etapas de desarrollo.
- **[Flujo de Trabajo Incremental](./docs/INCREMENTAL.md)** - Reglas de branching, PRs, commits y revisiones.

### 🏗️ Arquitectura y Diseño
- **[Arquitectura del Sistema](./docs/architecture.md)** - Descripción de la arquitectura de microservicios y tecnologías.
- **[Caso de Uso Principal](./docs/use-case.md)** - Flujo detallado de creación de pedido y asignación.

### 📊 Diagramas Visuales
- **[Diagrama de Etapas (Gantt)](./docs/etapas-incrementales.mmd)** - Timeline de desarrollo en formato Mermaid.
- **[Diagrama de Dependencias](./docs/etapas-dependencias.mmd)** - Relaciones entre etapas en formato Mermaid.

---

## Proceso de Desarrollo

Sigue estos pasos para comenzar tu proyecto:

1. Fork del repositorio https://github.com/UR-CC/plantilla-seminario, con un nombre relacionado con el proyecto de cada grupo.

2. Clonar el repositorio base:

    ```bash
    git clone https://github.com/USUARIO/nuevo-nombre.git 
    cd nuevo-nombre
    ```

2. Configuración inicial:
    Crea el archivo de variables de entorno a partir del ejemplo.

    ```bash
    cp .env.example .env
    ```

    **Nota**: Asegúrate de configurar las variables de entorno en el archivo `.env` si es necesario.

3. Familiarízate con la estructura del proyecto:
    
    * `frontend/`: La aplicación web principal (Flask).
    * `api-gateway/`: El enrutador de peticiones (FastAPI).
    * `services/`: Directorio donde desarrollarás tus microservicios (FastAPI).

    **Nota**: Hay comentarios `# TODO` que brindan indicaciones de lo que debe implementarse.

4. Selecciona uno de los temas propuestos.

5. Renombra los directorios de los microservicios `service[123]` según tu tema en la carpeta `services/`.

6. Revisa los archivos `main.py`, `Dockerfile`, y `requirements.txt` para cada uno de los microservicios.

7. Ajusta el archivo `docker-compose.yml` de tal forma que los servicios y bases de datos coincidan con tu tema.

8. Implementa la lógica de cada microservicio siguiendo los requisitos de tu tema.

    * Define e implementa tu modelo de datos.
    * Crea los endpoints de las API.
    * Implementa la comunicación entre servicios.
    * Conecta cada servicio a su base de datos.

### Ejecutar el Proyecto

Una vez que tengas tus servicios configurados, puedes levantar todo el stack con un solo comando:

```bash
docker-compose up --build
```

Esto construirá las imágenes y ejecutará todos los contenedores. Podrás acceder al frontend en `http://localhost:5000` y al API Gateway en `http://localhost:8000`.
