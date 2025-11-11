
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import uuid
import os
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, OrderORM, OrderItemORM
import time

app = FastAPI()

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@pedidos-db:5432/pedidos_db")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Item(BaseModel):
    item_id: str
    cantidad: int = Field(..., gt=0)


class OrderCreate(BaseModel):
    restaurante_id: str
    cliente_email: Optional[str]
    direccion: str
    items: List[Item]


class Repartidor(BaseModel):
    id: str
    nombre: str
    telefono: Optional[str] = None


class OrderOut(BaseModel):
    id: str
    restaurante_id: str
    cliente_email: Optional[str]
    direccion: str
    items: List[Dict]
    estado: str
    repartidor: Optional[Repartidor] = None


# service endpoints
REPARTIDORES_URL_BASE = os.getenv("REPARTIDORES_URL", "http://repartidores-service:8004/api/v1/repartidores")
RESTAURANTES_URL_BASE = os.getenv("RESTAURANTES_URL", "http://restaurantes-service:8002")


@app.on_event("startup")
def startup():
    attempts = 0
    while attempts < 10:
        try:
            Base.metadata.create_all(bind=engine)
            break
        except Exception:
            attempts += 1
            time.sleep(1)


@app.get("/")
def read_root():
    return {"message": "Servicio de pedidos en funcionamiento."}


@app.get("/health")
def health_check():
    return {"status": "ok"}


def _assign_repartidor() -> Optional[Repartidor]:
    """Call repartidores service and try to pick an available repartidor (simple round-robin by the remote service)."""
    try:
        resp = requests.get(REPARTIDORES_URL_BASE, timeout=2)
        if resp.status_code == 200:
            data = resp.json()
            pool = data.get('repartidores') if isinstance(data, dict) else (data if isinstance(data, list) else [])
            # pick first available
            for p in pool:
                if not p.get('estado') or p.get('estado') == 'disponible':
                    return Repartidor(**p)
    except Exception:
        pass
    return None


@app.post("/api/v1/pedidos", response_model=OrderOut)
def create_pedido(payload: OrderCreate):
    """Crear un pedido: reserva items en restaurantes, persiste el pedido en DB y asigna repartidor."""
    order_id = str(uuid.uuid4())
    reserved = []
    # Pre-check stock by fetching the restaurant menu once. If any requested
    # item has cantidad == 0 (sin stock) or cantidad < requested cantidad,
    # reject the order early with 400 to avoid partial reservations.
    try:
        menu_url = f"{RESTAURANTES_URL_BASE}/api/v1/restaurantes/{payload.restaurante_id}/menu"
        mresp = requests.get(menu_url, timeout=2)
        if mresp.status_code == 200:
            menu = mresp.json().get("menu", []) if isinstance(mresp.json(), dict) else []
            stock_map = {it.get('id'): it.get('cantidad', 0) for it in menu}
            for it in payload.items:
                avail = stock_map.get(it.item_id)
                if avail is None:
                    # item not present in menu
                    raise HTTPException(status_code=400, detail=f"Item {it.item_id} no encontrado en el restaurante")
                if avail <= 0:
                    raise HTTPException(status_code=400, detail=f"Item {it.item_id} sin stock")
                if avail < it.cantidad:
                    raise HTTPException(status_code=400, detail=f"Stock insuficiente para item {it.item_id}")
    except HTTPException:
        # re-raise validation errors
        raise
    except Exception:
        # if we can't reach restaurantes or parsing fails, fall back to
        # attempting reservation as before (reserve calls will enforce stock)
        pass
    # Reserve items in restaurantes service
    for it in payload.items:
        url = f"{RESTAURANTES_URL_BASE}/api/v1/restaurantes/{payload.restaurante_id}/menu/{it.item_id}/reserve?cantidad={it.cantidad}"
        try:
            r = requests.post(url, timeout=3)
            if r.status_code != 200:
                # release previously reserved
                for prev in reserved:
                    try:
                        rel = f"{RESTAURANTES_URL_BASE}/api/v1/restaurantes/{payload.restaurante_id}/menu/{prev['item_id']}/release?cantidad={prev['cantidad']}"
                        requests.post(rel, timeout=2)
                    except Exception:
                        pass
                raise HTTPException(status_code=400, detail=f"No se pudo reservar item {it.item_id}")
            reserved.append({"item_id": it.item_id, "cantidad": it.cantidad, "resp": r.json()})
        except HTTPException:
            raise
        except Exception:
            for prev in reserved:
                try:
                    rel = f"{RESTAURANTES_URL_BASE}/api/v1/restaurantes/{payload.restaurante_id}/menu/{prev['item_id']}/release?cantidad={prev['cantidad']}"
                    requests.post(rel, timeout=2)
                except Exception:
                    pass
            raise HTTPException(status_code=500, detail="Error reservando items en restaurante")

    # persist order and items
    db = SessionLocal()
    try:
        order = OrderORM(id=order_id, restaurante_id=payload.restaurante_id, cliente_email=payload.cliente_email, direccion=payload.direccion, estado='creado')
        db.add(order)
        db.flush()
        items_out = []
        for rsv in reserved:
            item_info = rsv['resp']
            oi = OrderItemORM(order_id=order_id, item_id=item_info.get('id'), nombre=item_info.get('nombre'), precio=item_info.get('precio'), cantidad=rsv['cantidad'])
            db.add(oi)
            items_out.append({"item_id": oi.item_id, "nombre": oi.nombre, "precio": float(oi.precio), "cantidad": oi.cantidad})
        db.commit()
    finally:
        db.close()

    # assign repartidor
    rep = _assign_repartidor()
    repartidor_out = None
    estado = 'creado'
    repartidor_snapshot = None
    if rep:
        try:
            assign_url = f"{REPARTIDORES_URL_BASE}/{rep.id}/assign"
            r = requests.post(assign_url, timeout=2)
            if r.status_code == 200:
                repartidor_out = r.json()
                estado = 'asignado'
                # snapshot the repartidor info to store in DB
                repartidor_snapshot = {
                    'id': repartidor_out.get('id'),
                    'nombre': repartidor_out.get('nombre'),
                    'telefono': repartidor_out.get('telefono')
                }
        except Exception:
            pass

    # update order estado and persist repartidor snapshot in DB
    db = SessionLocal()
    try:
        o = db.query(OrderORM).filter(OrderORM.id == order_id).first()
        if o:
            o.estado = estado
            if repartidor_snapshot:
                o.repartidor_id = repartidor_snapshot.get('id')
                o.repartidor_nombre = repartidor_snapshot.get('nombre')
                o.repartidor_telefono = repartidor_snapshot.get('telefono')
            db.add(o)
            db.commit()
    finally:
        db.close()

    return {
        "id": order_id,
        "restaurante_id": payload.restaurante_id,
        "cliente_email": payload.cliente_email,
        "direccion": payload.direccion,
        "items": items_out,
        "estado": estado,
        "repartidor": repartidor_out,
    }


@app.get("/api/v1/pedidos/{order_id}", response_model=OrderOut)
def get_pedido(order_id: str):
    db = SessionLocal()
    try:
        o = db.query(OrderORM).filter(OrderORM.id == order_id).first()
        if not o:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        items = []
        for it in o.items:
            items.append({"item_id": it.item_id, "nombre": it.nombre, "precio": float(it.precio), "cantidad": it.cantidad})
        repartidor = None
        if getattr(o, 'repartidor_id', None) or getattr(o, 'repartidor_nombre', None):
            repartidor = {
                'id': getattr(o, 'repartidor_id', None),
                'nombre': getattr(o, 'repartidor_nombre', None),
                'telefono': getattr(o, 'repartidor_telefono', None)
            }
        return {"id": o.id, "restaurante_id": o.restaurante_id, "cliente_email": o.cliente_email, "direccion": o.direccion, "items": items, "estado": o.estado, "repartidor": repartidor}
    finally:
        db.close()


@app.post("/api/v1/pedidos/{order_id}/complete", response_model=OrderOut)
def complete_pedido(order_id: str):
    db = SessionLocal()
    try:
        o = db.query(OrderORM).filter(OrderORM.id == order_id).first()
        if not o:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        if o.estado == 'completado':
            items = [{"item_id": it.item_id, "nombre": it.nombre, "precio": float(it.precio), "cantidad": it.cantidad} for it in o.items]
            return {"id": o.id, "restaurante_id": o.restaurante_id, "cliente_email": o.cliente_email, "direccion": o.direccion, "items": items, "estado": o.estado, "repartidor": None}

        # Release reserved items back to restaurante (increase stock)
        for it in o.items:
            try:
                rel = f"{RESTAURANTES_URL_BASE}/api/v1/restaurantes/{o.restaurante_id}/menu/{it.item_id}/release?cantidad={it.cantidad}"
                requests.post(rel, timeout=2)
            except Exception:
                pass

        # free repartidor is not tracked locally; try best-effort freeing via repartidores service
        # (we don't store which repartidor was assigned in DB in this simple implementation)

        o.estado = 'completado'
        db.add(o)
        db.commit()
        items = [{"item_id": it.item_id, "nombre": it.nombre, "precio": float(it.precio), "cantidad": it.cantidad} for it in o.items]
        return {"id": o.id, "restaurante_id": o.restaurante_id, "cliente_email": o.cliente_email, "direccion": o.direccion, "items": items, "estado": o.estado, "repartidor": None}
    finally:
        db.close()

