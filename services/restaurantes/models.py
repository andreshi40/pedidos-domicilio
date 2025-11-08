from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from pydantic import BaseModel
from typing import Optional, List


# Declarative base used by the service
Base = declarative_base()


class RestauranteORM(Base):
    __tablename__ = "restaurantes"

    id = Column(String, primary_key=True, index=True)
    nombre = Column(String, nullable=False)
    direccion = Column(String)
    descripcion = Column(String)
    rating = Column(Float, nullable=True)

    menu = relationship("MenuItemORM", back_populates="restaurante", cascade="all, delete-orphan")

    def to_dict(self):
        return {
            "id": self.id,
            "nombre": self.nombre,
            "direccion": self.direccion,
            "descripcion": self.descripcion,
            "rating": float(self.rating) if self.rating is not None else None,
        }


class MenuItemORM(Base):
    __tablename__ = "menu_items"

    id = Column(String, primary_key=True, index=True)
    restaurante_id = Column(String, ForeignKey("restaurantes.id"), index=True)
    nombre = Column(String, nullable=False)
    precio = Column(Float, nullable=False)
    cantidad = Column(Integer, nullable=False, default=0)

    restaurante = relationship("RestauranteORM", back_populates="menu")

    def to_dict(self):
        return {
            "id": self.id,
            "restaurante_id": self.restaurante_id,
            "nombre": self.nombre,
            "precio": float(self.precio),
            "cantidad": int(self.cantidad),
        }


# Pydantic models for API responses/validation
class MenuItem(BaseModel):
    id: str
    nombre: str
    precio: float
    cantidad: int


class Restaurante(BaseModel):
    id: str
    nombre: str
    direccion: Optional[str] = None
    descripcion: Optional[str] = None
    rating: Optional[float] = None

    class Config:
        orm_mode = True
