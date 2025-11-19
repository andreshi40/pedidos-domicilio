from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional, Dict
import uuid
import os
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, OrderORM, OrderItemORM
import time
import threading

app = FastAPI()

# Database setup
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://user:password@pedidos-db:5432/pedidos_db"
)
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Item(BaseModel):
    item_id: str
    cantidad: int = Field(..., gt=0)


class OrderCreate(BaseModel):
    restaurante_id: str
    cliente_email: Optional[str]
    nombre_cliente: Optional[str] = None
    apellido_cliente: Optional[str] = None
    telefono_cliente: Optional[str] = None
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
    nombre_cliente: Optional[str] = None
    apellido_cliente: Optional[str] = None
    telefono_cliente: Optional[str] = None
    direccion: str
    items: List[Dict]
    estado: str
    repartidor: Optional[Repartidor] = None


# service endpoints
REPARTIDORES_URL_BASE = os.getenv(
    "REPARTIDORES_URL", "http://repartidores-service:8004/api/v1/repartidores"
)
RESTAURANTES_URL_BASE = os.getenv(
    "RESTAURANTES_URL", "http://restaurantes-service:8002"
)
BACKGROUND_ASSIGN_INTERVAL = int(os.getenv("BACKGROUND_ASSIGN_INTERVAL", "5"))


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
    """Call repartidores service atomically to assign the next available repartidor.

    Uses the new endpoint POST /assign-next which will return 200 and the assigned
    repartidor JSON, or 204 if none available. This reduces races compared to the
    previous GET-then-assign pattern.
    """
    try:
        assign_url = f"{REPARTIDORES_URL_BASE}/assign-next"
        resp = requests.post(assign_url, timeout=3)
        if resp.status_code == 200:
            return Repartidor(**resp.json())
        if resp.status_code == 204:
            return None
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
        menu_url = (
            f"{RESTAURANTES_URL_BASE}/api/v1/restaurantes/{payload.restaurante_id}/menu"
        )
        mresp = requests.get(menu_url, timeout=2)
        if mresp.status_code == 200:
            menu = (
                mresp.json().get("menu", []) if isinstance(mresp.json(), dict) else []
            )
            stock_map = {it.get("id"): it.get("cantidad", 0) for it in menu}
            for it in payload.items:
                avail = stock_map.get(it.item_id)
                if avail is None:
                    # item not present in menu
                    raise HTTPException(
                        status_code=400,
                        detail=f"Item {it.item_id} no encontrado en el restaurante",
                    )
                if avail <= 0:
                    raise HTTPException(
                        status_code=400, detail=f"Item {it.item_id} sin stock"
                    )
                if avail < it.cantidad:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Stock insuficiente para item {it.item_id}",
                    )
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
                raise HTTPException(
                    status_code=400, detail=f"No se pudo reservar item {it.item_id}"
                )
            reserved.append(
                {"item_id": it.item_id, "cantidad": it.cantidad, "resp": r.json()}
            )
        except HTTPException:
            raise
        except Exception:
            for prev in reserved:
                try:
                    rel = f"{RESTAURANTES_URL_BASE}/api/v1/restaurantes/{payload.restaurante_id}/menu/{prev['item_id']}/release?cantidad={prev['cantidad']}"
                    requests.post(rel, timeout=2)
                except Exception:
                    pass
            raise HTTPException(
                status_code=500, detail="Error reservando items en restaurante"
            )

    # persist order and items
    db = SessionLocal()
    try:
        order = OrderORM(
            id=order_id,
            restaurante_id=payload.restaurante_id,
            cliente_email=payload.cliente_email,
            nombre_cliente=payload.nombre_cliente,
            apellido_cliente=payload.apellido_cliente,
            telefono_cliente=payload.telefono_cliente,
            direccion=payload.direccion,
            estado="creado",
            created_at=datetime.utcnow(),
        )
        db.add(order)
        db.flush()
        items_out = []
        for rsv in reserved:
            item_info = rsv["resp"]
            oi = OrderItemORM(
                order_id=order_id,
                item_id=item_info.get("id"),
                nombre=item_info.get("nombre"),
                precio=item_info.get("precio"),
                cantidad=rsv["cantidad"],
            )
            db.add(oi)
            items_out.append(
                {
                    "item_id": oi.item_id,
                    "nombre": oi.nombre,
                    "precio": float(oi.precio),
                    "cantidad": oi.cantidad,
                }
            )
        db.commit()

        # Try to assign a repartidor immediately; persist snapshot if assigned.
        try:
            rep = _assign_repartidor()
            if rep:
                # reload session and update order with repartidor snapshot
                o = db.query(OrderORM).filter(OrderORM.id == order_id).first()
                if o:
                    o.repartidor_id = rep.id
                    o.repartidor_nombre = rep.nombre
                    o.repartidor_telefono = rep.telefono
                    o.estado = "asignado"
                    db.add(o)
                    db.commit()
        except Exception:
            # best-effort: if assignment fails, keep order in 'creado' and let background assigner retry
            try:
                db.rollback()
            except Exception:
                pass
        # Build response payload
        repartidor_out = None
        o = db.query(OrderORM).filter(OrderORM.id == order_id).first()
        if o and getattr(o, "repartidor_id", None):
            repartidor_out = {
                "id": o.repartidor_id,
                "nombre": o.repartidor_nombre,
                "telefono": o.repartidor_telefono,
            }
        return {
            "id": order_id,
            "restaurante_id": payload.restaurante_id,
            "cliente_email": payload.cliente_email,
            "nombre_cliente": payload.nombre_cliente,
            "apellido_cliente": payload.apellido_cliente,
            "telefono_cliente": payload.telefono_cliente,
            "direccion": payload.direccion,
            "items": items_out,
            "estado": o.estado if o else "creado",
            "repartidor": repartidor_out,
        }
    finally:
        db.close()


@app.get("/api/v1/repartidor/{rep_id}/orders")
def orders_for_repartidor(rep_id: str, year: int = None, month: int = None):
    """Return orders assigned to a repartidor filtered by year/month.

    Returns list of orders (id, estado, created_at, total) and aggregates:
    - current_order (if any non-completed order exists, the most recent)
    - gain_current: 10% of current order total
    - gain_others: sum of 10% of other orders in the month
    - orders: list of orders for the month
    """
    db = SessionLocal()
    try:
        q = db.query(OrderORM).filter(OrderORM.repartidor_id == rep_id)
        # filter by month/year if provided
        if year and month:
            start = datetime(year, month, 1)
            # compute first day of next month
            if month == 12:
                end = datetime(year + 1, 1, 1)
            else:
                end = datetime(year, month + 1, 1)
            q = q.filter(OrderORM.created_at >= start, OrderORM.created_at < end)

        rows = q.order_by(OrderORM.created_at.desc()).all()
        orders = []
        total_month_gain = 0.0
        current_order = None
        for o in rows:
            total = 0.0
            items_list = []
            for it in o.items:
                total += float(it.precio) * int(it.cantidad)
                items_list.append(
                    {
                        "nombre": it.nombre,
                        "precio": float(it.precio),
                        "cantidad": it.cantidad,
                    }
                )
            orders.append(
                {
                    "id": o.id,
                    "estado": o.estado,
                    "created_at": o.created_at.isoformat(),
                    "total": total,
                    "items": items_list,
                }
            )
            # accumulate gain as 10% of total
            total_month_gain += total * 0.10
            # pick the most recent non-completed order as current
            if not current_order and o.estado != "completado":
                current_order = {
                    "id": o.id,
                    "estado": o.estado,
                    "created_at": o.created_at.isoformat(),
                    "total": total,
                    "items": items_list,
                }

        gain_current = current_order["total"] * 0.10 if current_order else 0.0
        # total of other orders = total_month_gain - gain_current
        gain_others = round(max(0.0, total_month_gain - (gain_current)), 2)
        return {
            "orders": orders,
            "current_order": current_order,
            "gain_current": round(gain_current, 2),
            "gain_others": gain_others,
        }
    finally:
        db.close()


# Background assigner: periodically scans for orders in 'creado' without repartidor
# and attempts to assign using the repartidores assign-next endpoint. This reduces
# the chance an order remains unassigned if initial assignment failed due to no
# available repartidores.
def _background_assigner_loop():
    while True:
        try:
            db = SessionLocal()
            try:
                pending = db.query(OrderORM).filter(OrderORM.estado == "creado").all()
                if pending:
                    print(
                        f"[PEDIDOS][ASSIGNER] found {len(pending)} pending orders",
                        flush=True,
                    )
                for o in pending:
                    # skip if already has repartidor snapshot
                    if getattr(o, "repartidor_id", None):
                        continue
                    try:
                        assign_url = f"{REPARTIDORES_URL_BASE}/assign-next"
                        print(
                            f"[PEDIDOS][ASSIGNER] trying assign-next for order {o.id}",
                            flush=True,
                        )
                        r = requests.post(assign_url, timeout=3)
                        print(
                            f"[PEDIDOS][ASSIGNER] assign-next responded {getattr(r, 'status_code', 'ERR')}",
                            flush=True,
                        )
                        if r.status_code == 200:
                            rep = r.json()
                            o.repartidor_id = rep.get("id")
                            o.repartidor_nombre = rep.get("nombre")
                            o.repartidor_telefono = rep.get("telefono")
                            o.estado = "asignado"
                            db.add(o)
                            db.commit()
                            print(
                                f"[PEDIDOS][ASSIGNER] order {o.id} assigned to {rep.get('id')}",
                                flush=True,
                            )
                        else:
                            # no repartidor available (204) or other status
                            pass
                    except Exception as ex:
                        # ignore and continue with next order but log the exception
                        try:
                            db.rollback()
                        except Exception:
                            pass
                        print(
                            f"[PEDIDOS][ASSIGNER] exception while assigning order {getattr(o, 'id', '?')}: {ex}",
                            flush=True,
                        )
                        continue
            finally:
                db.close()
        except Exception:
            # top-level protection: sleep and continue
            pass
        time.sleep(BACKGROUND_ASSIGN_INTERVAL)


@app.on_event("startup")
def start_background_assigner():
    # Start the background assigner in a safe wrapper so that any unexpected
    # exception inside the thread won't propagate and crash the FastAPI process
    # during startup. We also protect the thread creation itself.
    def _safe_runner():
        try:
            _background_assigner_loop()
        except Exception as e:
            # Log the exception and keep the thread from raising further
            print(f"[PEDIDOS] background assigner crashed: {e}", flush=True)

    try:
        t = threading.Thread(target=_safe_runner, daemon=True, name="assigner-thread")
        t.start()
        print("[PEDIDOS] background assigner started", flush=True)
    except Exception as e:
        # Don't let a thread-start failure kill the whole app at startup
        print(f"[PEDIDOS] failed to start background assigner: {e}", flush=True)


@app.get("/api/v1/pedidos/{order_id}", response_model=OrderOut)
def get_pedido(order_id: str):
    db = SessionLocal()
    try:
        o = db.query(OrderORM).filter(OrderORM.id == order_id).first()
        if not o:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        items = []
        for it in o.items:
            items.append(
                {
                    "item_id": it.item_id,
                    "nombre": it.nombre,
                    "precio": float(it.precio),
                    "cantidad": it.cantidad,
                }
            )
        repartidor = None
        if getattr(o, "repartidor_id", None) or getattr(o, "repartidor_nombre", None):
            repartidor = {
                "id": getattr(o, "repartidor_id", None),
                "nombre": getattr(o, "repartidor_nombre", None),
                "telefono": getattr(o, "repartidor_telefono", None),
            }
        return {
            "id": o.id,
            "restaurante_id": o.restaurante_id,
            "cliente_email": o.cliente_email,
            "nombre_cliente": getattr(o, "nombre_cliente", None),
            "apellido_cliente": getattr(o, "apellido_cliente", None),
            "telefono_cliente": getattr(o, "telefono_cliente", None),
            "direccion": o.direccion,
            "items": items,
            "estado": o.estado,
            "repartidor": repartidor,
        }
    finally:
        db.close()


@app.post("/api/v1/pedidos/{order_id}/complete", response_model=OrderOut)
def complete_pedido(order_id: str):
    db = SessionLocal()
    try:
        o = db.query(OrderORM).filter(OrderORM.id == order_id).first()
        if not o:
            raise HTTPException(status_code=404, detail="Pedido no encontrado")
        if o.estado == "completado":
            items = [
                {
                    "item_id": it.item_id,
                    "nombre": it.nombre,
                    "precio": float(it.precio),
                    "cantidad": it.cantidad,
                }
                for it in o.items
            ]
            return {
                "id": o.id,
                "restaurante_id": o.restaurante_id,
                "cliente_email": o.cliente_email,
                "direccion": o.direccion,
                "items": items,
                "estado": o.estado,
                "repartidor": None,
            }

        # Release reserved items back to restaurante (increase stock)
        for it in o.items:
            try:
                rel = f"{RESTAURANTES_URL_BASE}/api/v1/restaurantes/{o.restaurante_id}/menu/{it.item_id}/release?cantidad={it.cantidad}"
                requests.post(rel, timeout=2)
            except Exception:
                pass

        # Free repartidor if assigned
        if o.repartidor_id:
            try:
                free_url = f"{REPARTIDORES_URL_BASE}/{o.repartidor_id}/free"
                resp = requests.post(free_url, timeout=2)
                print(
                    f"Freed repartidor {o.repartidor_id}: status {resp.status_code}",
                    flush=True,
                )
            except Exception as e:
                # Log but don't fail the completion
                print(
                    f"Warning: Failed to free repartidor {o.repartidor_id}: {e}",
                    flush=True,
                )

        o.estado = "completado"
        db.add(o)
        db.commit()
        items = [
            {
                "item_id": it.item_id,
                "nombre": it.nombre,
                "precio": float(it.precio),
                "cantidad": it.cantidad,
            }
            for it in o.items
        ]
        return {
            "id": o.id,
            "restaurante_id": o.restaurante_id,
            "cliente_email": o.cliente_email,
            "direccion": o.direccion,
            "items": items,
            "estado": o.estado,
            "repartidor": None,
        }
    finally:
        db.close()


@app.get("/api/v1/restaurante/{restaurante_id}/orders")
def orders_for_restaurante(restaurante_id: str, year: int = None, month: int = None):
    """Return orders for a restaurant filtered by year/month with statistics.

    Returns:
    - orders: list of all orders for the period
    - stats_day: sales by day
    - stats_month: total sales for the month
    - pending_count: number of pending orders (not completed)
    - completed_count: number of completed orders
    """
    db = SessionLocal()
    try:
        q = db.query(OrderORM).filter(OrderORM.restaurante_id == restaurante_id)

        # filter by month/year if provided
        if year and month:
            start = datetime(year, month, 1)
            if month == 12:
                end = datetime(year + 1, 1, 1)
            else:
                end = datetime(year, month + 1, 1)
            q = q.filter(OrderORM.created_at >= start, OrderORM.created_at < end)

        rows = q.order_by(OrderORM.created_at.desc()).all()

        orders = []
        pending_count = 0
        completed_count = 0
        total_month = 0.0
        stats_by_day = {}

        for o in rows:
            # Calculate order total
            total = 0.0
            items_list = []
            for it in o.items:
                subtotal = float(it.precio) * int(it.cantidad)
                total += subtotal
                items_list.append(
                    {
                        "nombre": it.nombre,
                        "precio": float(it.precio),
                        "cantidad": it.cantidad,
                        "subtotal": round(subtotal, 2),
                    }
                )

            # Count by status
            if o.estado == "completado":
                completed_count += 1
            else:
                pending_count += 1

            # Accumulate totals
            total_month += total

            # Group by day
            day_key = o.created_at.strftime("%Y-%m-%d")
            if day_key not in stats_by_day:
                stats_by_day[day_key] = {"date": day_key, "total": 0.0, "count": 0}
            stats_by_day[day_key]["total"] += total
            stats_by_day[day_key]["count"] += 1

            orders.append(
                {
                    "id": o.id,
                    "cliente_email": o.cliente_email,
                    "nombre_cliente": getattr(o, "nombre_cliente", None),
                    "apellido_cliente": getattr(o, "apellido_cliente", None),
                    "telefono_cliente": getattr(o, "telefono_cliente", None),
                    "direccion": o.direccion,
                    "estado": o.estado,
                    "repartidor_nombre": getattr(o, "repartidor_nombre", None),
                    "created_at": o.created_at.isoformat(),
                    "total": round(total, 2),
                    "items": items_list,
                }
            )

        # Convert stats_by_day to sorted list
        stats_day = sorted(stats_by_day.values(), key=lambda x: x["date"], reverse=True)
        for day in stats_day:
            day["total"] = round(day["total"], 2)

        return {
            "orders": orders,
            "stats_day": stats_day,
            "stats_month": {
                "total": round(total_month, 2),
                "orders_count": len(orders),
                "pending_count": pending_count,
                "completed_count": completed_count,
            },
        }
    finally:
        db.close()
