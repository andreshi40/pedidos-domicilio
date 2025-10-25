from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# TODO: Importa la base declarativa del archivo models.py
# from .models import Base

# Obtiene la URL de la base de datos de las variables de entorno.
# Asegúrate de que esta variable esté definida en el archivo docker-compose.yml.
DATABASE_URL = os.getenv("DATABASE_URL")

# Crea el motor de la base de datos.
# El argumento echo=True muestra todas las sentencias SQL ejecutadas (útil para debug).
engine = create_engine(DATABASE_URL, echo=True)

# Configura la sesión de la base de datos.
# Esta clase creará nuevas sesiones de base de datos.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Función para crear todas las tablas en la base de datos.
def create_db_and_tables():
    """Crea todas las tablas definidas en models.py si no existen."""
    Base.metadata.create_all(bind=engine)

# Define la dependencia para la sesión de la base de datos.
# Esta función se usará en los endpoints de FastAPI para obtener una sesión de DB.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
