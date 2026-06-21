"""Jarvis web sunucusu - FastAPI.

Tarayıcı arayüzünü sunar ve /chat endpoint'i ile beyne bağlanır.
Yerel makinede çalışır, böylece sistem kontrolü mümkündür.
"""
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

import brain
import memory

app = FastAPI(title="Jarvis", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"


class ChatResponse(BaseModel):
    reply: str


@app.on_event("startup")
def _startup():
    memory.init_db()


@app.get("/health")
def health():
    return brain.health()


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    reply = brain.chat(req.message, req.session_id)
    return ChatResponse(reply=reply)


@app.post("/reset")
def reset(req: ChatRequest):
    memory.clear_session(req.session_id)
    return {"status": "ok"}


# Frontend statik dosyaları (en sona koy ki API yolları öncelikli olsun)
@app.get("/")
def index():
    return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))


app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
