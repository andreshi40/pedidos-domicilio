from fastapi import FastAPI, HTTPException, UploadFile, File, Request
from fastapi.responses import FileResponse
from typing import Optional
from sqlalchemy.orm import Session
import database_sql
from models import RestauranteORM, MenuItemORM
import time
import os
import shutil

app = FastAPI()


def seed_db_if_empty() -> None:
    db: Session = database_sql.SessionLocal()
    try:
        if db.query(RestauranteORM).count() == 0:
            defaults = [
                RestauranteORM(
                    id="rest1",
                    nombre="La Pizzeria",
                    direccion="Calle Luna 12",
                    descripcion="Pizzas artesanales y buenos postres",
                    rating=4.6,
                ),
                RestauranteORM(
                    id="rest2",
                    nombre="Sushi Express",
                    direccion="Avenida Sol 45",
                    descripcion="Sushi fresco para llevar",
                    rating=4.4,
                ),
                RestauranteORM(
                    id="rest3",
                    nombre="Taco House",
                    direccion="Plaza Centro 3",
                    descripcion="Tacos, burritos y sabores mexicanos",
                    rating=4.2,
                ),
            ]
            db.add_all(defaults)
            db.commit()

            menu_defaults = [
                MenuItemORM(
                    id="p1",
                    restaurante_id="rest1",
                    nombre="Margarita",
                    precio=7.5,
                    cantidad=10,
                ),
                MenuItemORM(
                    id="p2",
                    restaurante_id="rest1",
                    nombre="Cuatro Quesos",
                    precio=9.0,
                    cantidad=5,
                ),
                MenuItemORM(
                    id="s1",
                    restaurante_id="rest2",
                    nombre="Sushi Mix 8",
                    precio=12.0,
                    cantidad=8,
                ),
                MenuItemORM(
                    id="s2",
                    restaurante_id="rest2",
                    nombre="California Roll",
                    precio=8.5,
                    cantidad=6,
                ),
                MenuItemORM(
                    id="t1",
                    restaurante_id="rest3",
                    nombre="Taco al Pastor",
                    precio=2.5,
                    cantidad=30,
                ),
                MenuItemORM(
                    id="t2",
                    restaurante_id="rest3",
                    nombre="Burrito Grande",
                    precio=6.5,
                    cantidad=10,
                ),
            ]
            db.add_all(menu_defaults)
            db.commit()
    finally:
        db.close()


@app.on_event("startup")
def startup() -> None:
    # Create photos directory if it doesn't exist
    photos_dir = os.path.join(os.getcwd(), "data", "restaurante_photos")
    os.makedirs(photos_dir, exist_ok=True)

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
            query = query.filter(
                RestauranteORM.nombre.ilike(like)
                | RestauranteORM.descripcion.ilike(like)
            )
        rows = query.limit(max(1, limit)).all()
        return {"restaurantes": [r.to_dict() for r in rows]}
    finally:
        db.close()


@app.get("/api/v1/restaurantes/by-user/{user_id}")
def get_restaurante_by_user(user_id: str):
    """Get restaurant by user_id."""
    db = database_sql.SessionLocal()
    try:
        r = db.query(RestauranteORM).filter(RestauranteORM.user_id == user_id).first()
        if not r:
            raise HTTPException(
                status_code=404, detail="No se encontró restaurante para este usuario"
            )
        return r.to_dict()
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
        items = (
            db.query(MenuItemORM).filter(MenuItemORM.restaurante_id == rest_id).all()
        )
        return {"menu": [i.to_dict() for i in items]}
    finally:
        db.close()


@app.post("/api/v1/restaurantes")
def create_restaurante(payload: dict, request: Request):
    """Create a restaurant. Expects JSON with at least 'nombre'. If 'id' is provided it will be used, otherwise generated."""
    db = database_sql.SessionLocal()
    try:
        nombre = payload.get("nombre") if isinstance(payload, dict) else None
        if not nombre:
            raise HTTPException(status_code=400, detail="'nombre' is required")
        rest_id = payload.get("id") or f"rest_{int(time.time() * 1000)}"
        existing = db.query(RestauranteORM).filter(RestauranteORM.id == rest_id).first()
        if existing:
            raise HTTPException(
                status_code=400, detail="Restaurante with given id already exists"
            )

        # Get user_id from headers (set by API Gateway from JWT token)
        user_id = request.headers.get("X-User-Id")

        r = RestauranteORM(
            id=rest_id,
            nombre=nombre,
            direccion=payload.get("direccion"),
            descripcion=payload.get("descripcion"),
            user_id=user_id,
        )
        db.add(r)
        db.commit()
        return r.to_dict()
    finally:
        db.close()


@app.post("/api/v1/restaurantes/{rest_id}/menu")
def create_menu_item(rest_id: str, payload: dict):
    """Create a menu item for a restaurant. Expects 'id' (optional), 'nombre', 'precio' and optional 'cantidad'."""
    db = database_sql.SessionLocal()
    try:
        nombre = payload.get("nombre") if isinstance(payload, dict) else None
        precio = payload.get("precio") if isinstance(payload, dict) else None
        if not nombre or precio is None:
            raise HTTPException(
                status_code=400, detail="'nombre' and 'precio' are required"
            )
        item_id = payload.get("id") or f"item_{int(time.time() * 1000)}"
        existing = (
            db.query(MenuItemORM)
            .filter(MenuItemORM.id == item_id, MenuItemORM.restaurante_id == rest_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=400, detail="Menu item with given id already exists"
            )
        item = MenuItemORM(
            id=item_id,
            restaurante_id=rest_id,
            nombre=nombre,
            precio=float(precio),
            cantidad=int(payload.get("cantidad") or 0),
        )
        db.add(item)
        db.commit()
        return item.to_dict()
    finally:
        db.close()


@app.post("/api/v1/restaurantes/{rest_id}/menu/{item_id}/reserve")
def reserve_menu_item(rest_id: str, item_id: str, cantidad: int = 1):
    """Reserve (decrement) cantidad of a menu item if available.

    This uses a SELECT FOR UPDATE (SQLAlchemy with_for_update) to avoid
    race conditions when multiple concurrent reservations are attempted.
    """
    db = database_sql.SessionLocal()
    try:
        # lock the row for update to prevent overselling under concurrency
        item = (
            db.query(MenuItemORM)
            .with_for_update()
            .filter(MenuItemORM.id == item_id, MenuItemORM.restaurante_id == rest_id)
            .first()
        )
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
        item = (
            db.query(MenuItemORM)
            .filter(MenuItemORM.id == item_id, MenuItemORM.restaurante_id == rest_id)
            .first()
        )
        if not item:
            raise HTTPException(status_code=404, detail="Item no encontrado")
        item.cantidad = item.cantidad + cantidad
        db.add(item)
        db.commit()
        return item.to_dict()
    finally:
        db.close()


@app.delete("/api/v1/restaurantes/{rest_id}/menu/{item_id}")
def delete_menu_item(rest_id: str, item_id: str):
    """Delete a menu item from a restaurant."""
    db = database_sql.SessionLocal()
    try:
        item = (
            db.query(MenuItemORM)
            .filter(MenuItemORM.id == item_id, MenuItemORM.restaurante_id == rest_id)
            .first()
        )
        if not item:
            raise HTTPException(status_code=404, detail="Item no encontrado")
        db.delete(item)
        db.commit()
        return {"message": "Item eliminado correctamente", "id": item_id}
    finally:
        db.close()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/")
def read_root():
    return {"message": "Servicio de restaurantes funcionando."}


@app.post("/api/v1/restaurantes/{rest_id}/photo")
def upload_restaurante_photo(rest_id: str, file: UploadFile = File(...)):
    """Upload a photo/logo for a restaurant and store its URL in the DB.

    The file is saved under ./data/restaurante_photos/<rest_id>__<filename>
    and the DB `foto_url` column will store the relative path.
    Removes any existing photos for this restaurant before uploading the new one.
    """
    db = database_sql.SessionLocal()
    try:
        r = db.query(RestauranteORM).filter(RestauranteORM.id == rest_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Restaurante no encontrado")

        # ensure data dir exists
        data_dir = os.path.join(os.getcwd(), "data", "restaurante_photos")
        os.makedirs(data_dir, exist_ok=True)

        # Delete old photos for this restaurant
        try:
            for fname in os.listdir(data_dir):
                if fname.startswith(f"{rest_id}__"):
                    old_file = os.path.join(data_dir, fname)
                    if os.path.isfile(old_file):
                        os.remove(old_file)
        except Exception:
            pass  # Continue even if deletion fails

        # Save new photo with consistent naming
        safe_name = os.path.basename(file.filename)
        # Use timestamp to ensure uniqueness and avoid browser cache issues
        import time

        timestamp = int(time.time() * 1000)
        file_ext = os.path.splitext(safe_name)[1] if "." in safe_name else ".jpg"
        dest_path = os.path.join(data_dir, f"{rest_id}__{timestamp}{file_ext}")

        with open(dest_path, "wb") as out_f:
            shutil.copyfileobj(file.file, out_f)

        # store filename (we will serve via the GET /photo endpoint)
        filename = f"{rest_id}__{timestamp}{file_ext}"
        r.foto_url = filename
        db.add(r)
        db.commit()

        return {"foto_url": filename}
    finally:
        try:
            file.file.close()
        except Exception:
            pass
        db.close()


@app.get("/api/v1/restaurantes/{rest_id}/photo")
def get_restaurante_photo(rest_id: str):
    """Serve the uploaded photo for a restaurant (if present).

    The uploaded file is looked up in ./data/restaurante_photos using the
    foto_url from the database for the specific restaurant.
    """
    db = database_sql.SessionLocal()
    try:
        # Get the restaurant and its foto_url from DB
        r = db.query(RestauranteORM).filter(RestauranteORM.id == rest_id).first()
        if not r or not r.foto_url:
            raise HTTPException(status_code=404, detail="Foto no encontrada")

        data_dir = os.path.join(os.getcwd(), "data", "restaurante_photos")
        full_path = os.path.join(data_dir, r.foto_url)

        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            # If file doesn't exist, try to find any file with the rest_id prefix (fallback)
            if os.path.exists(data_dir):
                for fname in os.listdir(data_dir):
                    if fname.startswith(f"{rest_id}__"):
                        full_path = os.path.join(data_dir, fname)
                        if os.path.isfile(full_path):
                            return FileResponse(full_path)
            raise HTTPException(status_code=404, detail="Foto no encontrada")

        return FileResponse(full_path)
    finally:
        db.close()
