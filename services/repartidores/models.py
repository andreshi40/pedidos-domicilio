from sqlalchemy import Column, String
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class RepartidorORM(Base):
    __tablename__ = "repartidores"
    id = Column(String, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    telefono = Column(String, nullable=True)
    foto_url = Column(String, nullable=True)
    estado = Column(String, default="disponible")

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "telefono": self.telefono,
            "foto_url": self.foto_url,
            "estado": self.estado,
        }
