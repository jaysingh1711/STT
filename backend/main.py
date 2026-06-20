"""
main.py
--------
FastAPI application entrypoint for the Voice-to-Notes STT module.

Key responsibility: load the Faster-Whisper model EXACTLY ONCE during
server startup (via the lifespan handler) so it is never reloaded per
request or per WebSocket connection. This is critical for keeping
memory and CPU/GPU usage low when this module is embedded inside a
larger, already resource-constrained healthcare platform.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import router
from stt_service import STTService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ---- Startup: load the model once ----
    logger.info("Starting up Voice-to-Notes service...")
    STTService.load()
    yield
    # ---- Shutdown: place any cleanup here ----
    logger.info("Shutting down Voice-to-Notes service.")


app = FastAPI(
    title="MediScribe Voice-to-Notes API",
    description="Real-time speech-to-text module for clinical dictation.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: restrict allow_origins to your actual platform domain(s) in production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: e.g. ["https://your-healthcare-platform.com"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root():
    return {"service": "MediScribe Voice-to-Notes", "status": "running"}
