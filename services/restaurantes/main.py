from fastapi import FastAPI, HTTPException
from typing import Optional, List
from sqlalchemy.orm import Session
import database_sql
from models import RestauranteORM, MenuItemORM
import time

app = FastAPI()


def seed_db_if_empty() -> None:
    db: Session = database_sql.SessionLocal()
    try:
        if db.query(RestauranteORM).count() == 0:
            defaults = [
                RestauranteORM(id="rest1", nombre="La Pizzeria", direccion="Calle Luna 12", descripcion="Pizzas artesanales y buenos postres", rating=4.6),
                RestauranteORM(id="rest2", nombre="Sushi Express", direccion="Avenida Sol 45", descripcion="Sushi fresco para llevar", rating=4.4),
                RestauranteORM(id="rest3", nombre="Taco House", direccion="Plaza Centro 3", descripcion="Tacos, burritos y sabores mexicanos", rating=4.2),
            ]
            db.add_all(defaults)
            db.commit()

            menu_defaults = [
                MenuItemORM(id="p1", restaurante_id="rest1", nombre="Margarita", precio=7.5, cantidad=10),
                MenuItemORM(id="p2", restaurante_id="rest1", nombre="Cuatro Quesos", precio=9.0, cantidad=5),
                MenuItemORM(id="s1", restaurante_id="rest2", nombre="Sushi Mix 8", precio=12.0, cantidad=8),
                MenuItemORM(id="s2", restaurante_id="rest2", nombre="California Roll", precio=8.5, cantidad=6),
                MenuItemORM(id="t1", restaurante_id="rest3", nombre="Taco al Pastor", precio=2.5, cantidad=30),
                MenuItemORM(id="t2", restaurante_id="rest3", nombre="Burrito Grande", precio=6.5, cantidad=10),
            ]
            db.add_all(menu_defaults)
            db.commit()
    finally:
        db.close()


@app.on_event("startup")
def startup() -> None:
    # Try to create tables and seed with a small retry loop for DB readiness
    attempts = 0
    while attempts < 10:
        try:
            database_sql.create_db_and_tables()
            seed_db_if_empty()
            break
        except Exception:
            attempts += 1
            time.sleep(1)


@app.get("/api/v1/restaurantes")
def list_restaurantes(q: Optional[str] = None, limit: int = 20):
    db: Session = database_sql.SessionLocal()
    try:
        query = db.query(RestauranteORM)
        if q:
            like = f"%{q}%"
            query = query.filter(RestauranteORM.nombre.ilike(like) | RestauranteORM.descripcion.ilike(like))
        rows = query.limit(max(1, limit)).all()
        return {"restaurantes": [r.to_dict() for r in rows]}
    finally:
        db.close()


@app.get("/api/v1/restaurantes/{rest_id}")
def get_restaurante(rest_id: str):
    db = database_sql.SessionLocal()
    try:
        r = db.query(RestauranteORM).filter(RestauranteORM.id == rest_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Restaurante no encontrado")
        return r.to_dict()
    finally:
        db.close()


@app.get("/api/v1/restaurantes/{rest_id}/menu")
def get_menu(rest_id: str):
    db = database_sql.SessionLocal()
    try:
        items = db.query(MenuItemORM).filter(MenuItemORM.restaurante_id == rest_id).all()
        return {"menu": [i.to_dict() for i in items]}
    finally:
        db.close()


@app.post("/api/v1/restaurantes/{rest_id}/menu/{item_id}/reserve")
def reserve_menu_item(rest_id: str, item_id: str, cantidad: int = 1):
    """Reserve (decrement) cantidad of a menu item if available."""
    db = database_sql.SessionLocal()
    try:
        item = db.query(MenuItemORM).filter(MenuItemORM.id == item_id, MenuItemORM.restaurante_id == rest_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Item no encontrado")
        if item.cantidad < cantidad:
            raise HTTPException(status_code=400, detail="Cantidad insuficiente")
        item.cantidad = item.cantidad - cantidad
        db.add(item)
        db.commit()
        return item.to_dict()
    finally:
        db.close()


@app.post("/api/v1/restaurantes/{rest_id}/menu/{item_id}/release")
def release_menu_item(rest_id: str, item_id: str, cantidad: int = 1):
    """Release (increment) cantidad of a menu item (undo a reserve)."""
    db = database_sql.SessionLocal()
    try:
        item = db.query(MenuItemORM).filter(MenuItemORM.id == item_id, MenuItemORM.restaurante_id == rest_id).first()
        if not item:
            raise HTTPException(status_code=404, detail="Item no encontrado")
        item.cantidad = item.cantidad + cantidad
        db.add(item)
        db.commit()
        return item.to_dict()
    finally:
        db.close()


@app.get("/health")
def health_check():
    return {"status": "ok"}
