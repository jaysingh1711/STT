"""
main.py
--------
FastAPI application entrypoint for the Voice-to-Notes STT module.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import router
from stt_service import STTService
from database import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up Voice-to-Notes service...")
    STTService.load()
    init_db()
    yield
    logger.info("Shutting down Voice-to-Notes service.")


app = FastAPI(
    title="MediScribe Voice-to-Notes API",
    description="Real-time speech-to-text module for clinical dictation.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root():
    return {"service": "MediScribe Voice-to-Notes", "status": "running"}