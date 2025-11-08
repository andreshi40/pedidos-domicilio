from fastapi import FastAPI, HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from typing import List, Optional
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
                        RepartidorORM(id='r1', nombre='Carlos', telefono='+34123456789', estado='disponible'),
                        RepartidorORM(id='r2', nombre='Ana', telefono='+34198765432', estado='disponible'),
                        RepartidorORM(id='r3', nombre='Luis', telefono='+34900112233', estado='disponible'),
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
        r = RepartidorORM(id=payload.id, nombre=payload.nombre, telefono=payload.telefono, estado='disponible')
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


@app.post("/api/v1/repartidores/{rep_id}/assign")
def assign_repartidor(rep_id: str):
    db = SessionLocal()
    try:
        r = db.query(RepartidorORM).filter(RepartidorORM.id == rep_id).first()
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


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/")
def read_root():
    return {"message": "Servicio de repartidores en funcionamiento."}
