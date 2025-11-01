from datetime import datetime, timedelta
import os
from typing import Optional
import uuid

from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer
from pymongo import MongoClient
from bson.objectid import ObjectId
import redis
from dotenv import load_dotenv

load_dotenv()

SECRET_KEY = os.getenv("JWT_SECRET", "change-me-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60
REFRESH_TOKEN_EXPIRE_DAYS = 7

PWD_CONTEXT = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

MONGO_URL = os.getenv("AUTH_DATABASE_URL", "mongodb://auth-db:27017/auth_db")
client = MongoClient(MONGO_URL)
db = client.get_default_database()
users = db.get_collection("users")

# Ensure there's a unique index on email to prevent duplicates
try:
    users.create_index("email", unique=True)
except Exception:
    # ignore index creation errors at import time
    pass

# Redis for refresh token store (simple revoked/active list)
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
try:
    redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)
    # quick ping to ensure connection (will raise if unreachable)
    redis_client.ping()
except Exception:
    # If Redis isn't available at import time, set client to None and handle at runtime
    redis_client = None


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    role: Optional[str] = "cliente"


class Token(BaseModel):
    access_token: str
    token_type: str
    refresh_token: Optional[str] = None


app = FastAPI()


def verify_password(plain_password, hashed_password):
    return PWD_CONTEXT.verify(plain_password, hashed_password)


def get_password_hash(password):
    return PWD_CONTEXT.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_days: int = REFRESH_TOKEN_EXPIRE_DAYS):
    to_encode = data.copy()
    jti = str(uuid.uuid4())
    expire = datetime.utcnow() + timedelta(days=expires_days)
    to_encode.update({"exp": expire, "jti": jti})
    encoded = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    # store jti in redis with expiry so we can validate/ revoke
    if redis_client:
        try:
            redis_client.setex(f"refresh:{jti}", timedelta(days=expires_days), to_encode.get("sub"))
        except Exception:
            # ignore redis errors here; validation will fail if not present
            pass
    return encoded


@app.get("/")
def root():
    return {"message": "Authentication service", "health": "/health"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/register", response_model=dict)
def register(user: UserCreate):
    # check existing
    if users.find_one({"email": user.email}):
        raise HTTPException(status_code=409, detail="Email already registered")
    # basic password strength check
    if not user.password or len(user.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")
    hashed = get_password_hash(user.password)
    user_doc = {"email": user.email, "password": hashed, "role": user.role, "created_at": datetime.utcnow()}
    users.insert_one(user_doc)
    return {"message": "user created"}


@app.post("/login", response_model=Token)
def login(form_data: UserCreate):
    user = users.find_one({"email": form_data.email})
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    if not verify_password(form_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": str(user["_id"]), "email": user["email"], "role": user.get("role", "cliente")}, expires_delta=access_token_expires)
    refresh_token = create_refresh_token(data={"sub": str(user["_id"]), "email": user["email"], "role": user.get("role", "cliente")})
    return {"access_token": access_token, "token_type": "bearer", "refresh_token": refresh_token}


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/login")


def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("email")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = users.find_one({"email": email})
    if not user:
        raise credentials_exception
    # remove sensitive fields
    user.pop("password", None)
    user["id"] = str(user.pop("_id"))
    return user


def ensure_admin(current_user: dict = Depends(get_current_user)):
    """Dependency that raises if current user is not an admin."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
    return current_user


@app.get("/users")
def list_users(skip: int = 0, limit: int = 100, _admin=Depends(ensure_admin)):
    """List users (admin only). Returns users without passwords."""
    cursor = users.find({}, {"password": 0}).skip(skip).limit(limit)
    out = []
    for u in cursor:
        u["id"] = str(u.pop("_id"))
        out.append(u)
    return {"users": out}


@app.get("/users/{user_id}")
def get_user_by_id(user_id: str, current_user: dict = Depends(get_current_user)):
    """Get a user by id. Admins can fetch any user; users can fetch their own record."""
    # allow self or admin
    if current_user.get("id") != user_id and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to view this user")
    try:
        obj = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user id")
    u = users.find_one({"_id": obj}, {"password": 0})
    if not u:
        raise HTTPException(status_code=404, detail="User not found")
    u["id"] = str(u.pop("_id"))
    return {"user": u}


class RefreshRequest(BaseModel):
    refresh_token: str


@app.post("/refresh", response_model=Token)
def refresh_token(req: RefreshRequest):
    # validate refresh token, check jti exists in redis
    try:
        payload = jwt.decode(req.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        sub = payload.get("sub")
        if not jti or not sub:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    # check redis for jti
    if not redis_client:
        raise HTTPException(status_code=500, detail="Refresh service unavailable")

    stored = redis_client.get(f"refresh:{jti}")
    if not stored or str(stored) != str(sub):
        raise HTTPException(status_code=401, detail="Refresh token revoked or invalid")

    # issue new access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": str(sub), "email": payload.get("email"), "role": payload.get("role", "cliente")}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/logout", response_model=dict)
def logout(req: RefreshRequest):
    # revoke refresh token by deleting jti from redis
    try:
        payload = jwt.decode(req.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        sub = payload.get("sub")
        if not jti or not sub:
            raise HTTPException(status_code=401, detail="Invalid refresh token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    if not redis_client:
        # best-effort: if redis unavailable, inform user
        raise HTTPException(status_code=500, detail="Logout unavailable")

    removed = redis_client.delete(f"refresh:{jti}")
    if removed:
        return {"message": "logged out"}
    else:
        # already removed / invalid
        return {"message": "token not found or already revoked"}


@app.get("/me")
def read_current_user(current_user: dict = Depends(get_current_user)):
    return {"user": current_user}

