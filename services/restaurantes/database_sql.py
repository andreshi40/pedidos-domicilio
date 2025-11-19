from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Importa la base declarativa desde models
from models import Base

# Obtiene la URL de la base de datos de las variables de entorno.
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://user:password@restaurantes-db:5432/service1_db"
)

# Crea el motor y la sesión
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_db_and_tables():
    """Crea todas las tablas definidas en models.py si no existen."""
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
