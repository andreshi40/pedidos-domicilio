from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import Session
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional
from fastapi import UploadFile, File
import shutil
import os

from models import Base, RepartidorORM

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@repartidores-db:5432/repartidores_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

app = FastAPI()


class RepartidorIn(BaseModel):
    id: str
    nombre: str
    telefono: Optional[str] = None


class RepartidorOut(RepartidorIn):
    estado: str
    foto_url: Optional[str] = None


@app.on_event("startup")
def on_startup():
    # crear tablas si no existen; retry si la DB aún no está lista
    import time
    attempts = 0
    while attempts < 10:
        try:
            Base.metadata.create_all(bind=engine)
            # ensure there are initial repartidores
            db = SessionLocal()
            try:
                cnt = db.query(RepartidorORM).count()
                if cnt == 0:
                    defaults = [
                        RepartidorORM(id='r1', nombre='Carlos', telefono='+34123456789', estado='disponible', foto_url=None),
                        RepartidorORM(id='r2', nombre='Ana', telefono='+34198765432', estado='disponible', foto_url=None),
                        RepartidorORM(id='r3', nombre='Luis', telefono='+34900112233', estado='disponible', foto_url=None),
                    ]
                    for d in defaults:
                        db.add(d)
                    db.commit()
            finally:
                db.close()
            break
        except Exception:
            attempts += 1
            time.sleep(1)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/api/v1/repartidores")
def list_repartidores():
    db = SessionLocal()
    try:
        rows = db.query(RepartidorORM).all()
        return {"repartidores": [r.to_dict() for r in rows]}
    finally:
        db.close()


@app.post("/api/v1/repartidores", status_code=201)
def create_repartidor(payload: RepartidorIn):
    db = SessionLocal()
    try:
        existing = db.query(RepartidorORM).filter(RepartidorORM.id == payload.id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Repartidor ya existe")
        r = RepartidorORM(id=payload.id, nombre=payload.nombre, telefono=payload.telefono, estado='disponible', foto_url=None)
        db.add(r)
        db.commit()
        return r.to_dict()
    finally:
        db.close()


@app.get("/api/v1/repartidores/{rep_id}")
def get_repartidor(rep_id: str):
    db = SessionLocal()
    try:
        r = db.query(RepartidorORM).filter(RepartidorORM.id == rep_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Repartidor no encontrado")
        return r.to_dict()
    finally:
        db.close()



@app.post("/api/v1/repartidores/{rep_id}/photo")
def upload_repartidor_photo(rep_id: str, file: UploadFile = File(...)):
    """Upload a photo for a repartidor and store its URL in the DB.

    The file is saved under ./data/repartidor_photos/<rep_id>__<filename>
    and the DB `foto_url` column will store the relative path.
    """
    db = SessionLocal()
    try:
        r = db.query(RepartidorORM).filter(RepartidorORM.id == rep_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Repartidor no encontrado")
        # ensure data dir exists
        data_dir = os.path.join(os.getcwd(), 'data', 'repartidor_photos')
        os.makedirs(data_dir, exist_ok=True)
        safe_name = os.path.basename(file.filename)
        dest_path = os.path.join(data_dir, f"{rep_id}__{safe_name}")
        with open(dest_path, 'wb') as out_f:
            shutil.copyfileobj(file.file, out_f)
        # store relative path
        rel = f"/data/repartidor_photos/{rep_id}__{safe_name}"
        r.foto_url = rel
        db.add(r)
        db.commit()
        return {"foto_url": rel}
    finally:
        try:
            file.file.close()
        except Exception:
            pass
        db.close()


@app.post("/api/v1/repartidores/{rep_id}/assign")
def assign_repartidor(rep_id: str):
    # Use a DB transaction to avoid races when multiple callers try to
    # assign the same repartidor concurrently.
    db: Session = SessionLocal()
    try:
        # lock the row for update
        q = db.query(RepartidorORM).filter(RepartidorORM.id == rep_id).with_for_update()
        r = q.first()
        if not r:
            raise HTTPException(status_code=404, detail="Repartidor no encontrado")
        if r.estado == 'ocupado':
            raise HTTPException(status_code=400, detail="Repartidor ya ocupado")
        r.estado = 'ocupado'
        db.add(r)
        db.commit()
        return r.to_dict()
    finally:
        db.close()


@app.post("/api/v1/repartidores/{rep_id}/free")
def free_repartidor(rep_id: str):
    db = SessionLocal()
    try:
        r = db.query(RepartidorORM).filter(RepartidorORM.id == rep_id).first()
        if not r:
            raise HTTPException(status_code=404, detail="Repartidor no encontrado")
        r.estado = 'disponible'
        db.add(r)
        db.commit()
        return r.to_dict()
    finally:
        db.close()


@app.post("/api/v1/repartidores/assign-next")
def assign_next_repartidor():
    """Atomically pick and assign the next available repartidor.

    This endpoint performs a SELECT FOR UPDATE SKIP LOCKED to avoid race
    conditions when multiple callers attempt to get an available repartidor.
    Returns 200 with the assigned repartidor, or 204 if none available.
    """
    db: Session = SessionLocal()
    try:
        # Use a SELECT ... FOR UPDATE SKIP LOCKED to avoid races. SQLAlchemy
        # exposes this via with_for_update(skip_locked=True).
        q = db.query(RepartidorORM).filter(RepartidorORM.estado == 'disponible').with_for_update(skip_locked=True)
        r = q.first()
        if not r:
            return JSONResponse(status_code=204, content={})
        r.estado = 'ocupado'
        db.add(r)
        db.commit()
        return r.to_dict()
    finally:
        db.close()


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/")
def read_root():
    return {"message": "Servicio de repartidores en funcionamiento."}
