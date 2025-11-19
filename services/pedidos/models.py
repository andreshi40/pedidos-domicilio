from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, String, Integer, ForeignKey, Numeric
from sqlalchemy import DateTime
from datetime import datetime

Base = declarative_base()


class OrderORM(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, index=True)
    restaurante_id = Column(String, nullable=False)
    cliente_email = Column(String, nullable=True)
    nombre_cliente = Column(String, nullable=True)
    apellido_cliente = Column(String, nullable=True)
    telefono_cliente = Column(String, nullable=True)
    direccion = Column(String, nullable=False)
    estado = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    # store assigned repartidor info snapshot for easier queries and UI
    repartidor_id = Column(String, nullable=True)
    repartidor_nombre = Column(String, nullable=True)
    repartidor_telefono = Column(String, nullable=True)

    items = relationship(
        "OrderItemORM", back_populates="order", cascade="all, delete-orphan"
    )


class OrderItemORM(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    order_id = Column(String, ForeignKey("orders.id"), index=True)
    item_id = Column(String, nullable=False)
    nombre = Column(String, nullable=False)
    precio = Column(Numeric, nullable=False)
    cantidad = Column(Integer, nullable=False)

    order = relationship("OrderORM", back_populates="items")
