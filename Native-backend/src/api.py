# api.py
# NATIVE 2.0 — FastAPI backend

import sys
import asyncio
sys.path.insert(0, 'src')

from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
import bcrypt
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
import os

from database import create_tables, create_user, get_user_context, create_session
from level_detector import get_user_level
from context_builder import generate_session_summary

# Security config
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "native-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Password hashing
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI(title="NATIVE 2.0 API", version="1.0.0")

# CORS — allow React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables on startup
@app.on_event("startup")
async def startup():
    create_tables()

# ─── Models ───────────────────────────────────────────

class UserCreate(BaseModel):
    name: str
    password: str
    is_admin: bool = False

class Token(BaseModel):
    access_token: str
    token_type: str

class SessionStart(BaseModel):
    character: str

# ─── Auth helpers ─────────────────────────────────────

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password[:72].encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain[:72].encode(), hashed.encode())

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Simple in-memory user store for now
# TODO: migrate to SQLite auth table
USERS_DB = {}

def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        name: str = payload.get("sub")
        if name is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return name
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ─── Auth endpoints ───────────────────────────────────

@app.post("/register", response_model=Token)
async def register(user: UserCreate):
    if user.name in USERS_DB:
        raise HTTPException(status_code=400, detail="User already exists")
    
    user_id = create_user(user.name)
    USERS_DB[user.name] = {
        "password_hash": hash_password(user.password),
        "user_id": user_id,
        "is_admin": user.is_admin
    }
    
    token = create_access_token(
        data={"sub": user.name, "user_id": user_id},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": token, "token_type": "bearer"}

@app.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    user = USERS_DB.get(form_data.username)
    if not user or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    
    token = create_access_token(
        data={"sub": form_data.username, "user_id": user["user_id"]},
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": token, "token_type": "bearer"}

# ─── User endpoints ───────────────────────────────────

@app.get("/user/profile")
async def get_profile(current_user: str = Depends(get_current_user)):
    user_data = USERS_DB.get(current_user)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_id = user_data["user_id"]
    level = get_user_level(user_id)
    context = get_user_context(user_id)
    
    return {
        "name": current_user,
        "level": level,
        "avg_accuracy": context["avg_accuracy"],
        "avg_fluency": context["avg_fluency"],
        "frequent_errors": context["frequent_errors"][:3],
        "last_summary": context["last_summary"]
    }

# ─── Session endpoints ────────────────────────────────

@app.post("/session/start")
async def start_session(
    session: SessionStart,
    current_user: str = Depends(get_current_user)
):
    user_data = USERS_DB.get(current_user)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_id = user_data["user_id"]
    session_id = create_session(user_id, session.character)
    
    return {
        "session_id": session_id,
        "user_id": user_id,
        "character": session.character,
        "level": get_user_level(user_id)
    }

@app.get("/characters")
async def get_characters():
    return {
        "characters": [
            {"name": "Ava", "voice": "en-US-Ava:DragonHDLatestNeural", "description": "Warm and expressive"},
            {"name": "Emma", "voice": "en-US-Emma:DragonHDLatestNeural", "description": "Direct and witty"},
            {"name": "Andrew", "voice": "en-US-Andrew:DragonHDLatestNeural", "description": "Confident and natural"},
        ]
    }

@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}

@app.post("/session/{session_id}/summary")
async def create_session_summary(
    session_id: int,
    current_user: str = Depends(get_current_user)
):
    user_data = USERS_DB.get(current_user)
    if not user_data:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_id = user_data["user_id"]
    
    from context_builder import generate_session_summary
    from level_detector import update_level_from_session, get_user_level
    from database import get_connection
    
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT accuracy, fluency FROM progress
        WHERE user_id = ? AND session_id = ?
    """, (user_id, session_id))
    scores = [{"accuracy": r[0], "fluency": r[1]} for r in c.fetchall()]
    conn.close()
    
    new_level = update_level_from_session(user_id, scores)
    summary = await generate_session_summary(user_id, session_id, scores)
    
    return {
        "summary": summary,
        "level": new_level
    }

# ─── WebSocket Voice Live ─────────────────────────────

from voice_live import NativeVoiceLive

@app.websocket("/ws/voice/{session_id}/{character}/{user_name}/{user_id}")
async def voice_websocket(
    websocket: WebSocket,
    session_id: int,
    character: str,
    user_name: str,
    user_id: int
):
    await websocket.accept()
    
    try:
        assistant = NativeVoiceLive(
            character=character,
            user_name=user_name,
            user_id=user_id,
            session_id=session_id,
        )
        await assistant.start_websocket(websocket)
        
    except WebSocketDisconnect:
        print(f"Client disconnected - session {session_id}")
    except Exception as e:
        import traceback
        print(f"WebSocket error: {e}")
        print(traceback.format_exc())
        await websocket.close()
