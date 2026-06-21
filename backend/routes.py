"""
routes.py
----------
Defines the FastAPI HTTP + WebSocket routes for the Voice-to-Notes module.

Main endpoint: WS /ws/transcribe
  - Doctor's browser opens a WebSocket connection here.
  - Browser streams raw 16-bit PCM audio chunks (binary frames) over the
    socket as the doctor speaks.
  - Server buffers the audio, periodically runs Faster-Whisper over the
    buffer, and streams back partial transcripts.
  - When the browser sends a {"type": "stop"} control message (JSON text
    frame), the server finalizes the transcript and sends it back.
"""

import json
import logging
import uuid

import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from stt_service import STTService, SAMPLE_RATE
from websocket_manager import manager, PARTIAL_INTERVAL_SECONDS
from prescription_service import generate_prescription

logger = logging.getLogger("routes")
router = APIRouter()

MAX_BUFFER_SECONDS = 12.0


def pcm16_bytes_to_float32(data: bytes) -> np.ndarray:
    int16_array = np.frombuffer(data, dtype=np.int16)
    return int16_array.astype(np.float32) / 32768.0


@router.get("/health")
async def health_check():
    return {"status": "ok", "model_loaded": True}


class TranscriptRequest(BaseModel):
    transcript: str


@router.post("/generate-prescription")
async def generate_prescription_endpoint(payload: TranscriptRequest):
    try:
        result = await generate_prescription(payload.transcript)
        return result
    except RuntimeError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=str(e))


@router.websocket("/ws/transcribe")
async def websocket_transcribe(websocket: WebSocket):
    session_id = str(uuid.uuid4())
    stt = STTService.get()
    await manager.connect(session_id, websocket)

    try:
        while True:
            message = await websocket.receive()

            if message.get("bytes") is not None:
                pcm_chunk = pcm16_bytes_to_float32(message["bytes"])
                manager.append_audio(session_id, pcm_chunk)
                state = manager.get_session(session_id)

                buffer_seconds = len(state.audio_buffer) / SAMPLE_RATE

                if buffer_seconds >= MAX_BUFFER_SECONDS:
                    text = stt.transcribe(state.audio_buffer, partial=False)
                    if text:
                        state.confirmed_transcript = f"{state.confirmed_transcript} {text}".strip()
                    state.audio_buffer = np.empty(0, dtype=np.float32)
                    state.seconds_since_last_partial = 0.0
                    await manager.send_transcript(session_id, state.confirmed_transcript, is_final=False)

                elif state.seconds_since_last_partial >= PARTIAL_INTERVAL_SECONDS:
                    interim_text = stt.transcribe(state.audio_buffer, partial=True)
                    state.seconds_since_last_partial = 0.0
                    combined = f"{state.confirmed_transcript} {interim_text}".strip()
                    await manager.send_transcript(session_id, combined, is_final=False)

            elif message.get("text") is not None:
                try:
                    payload = json.loads(message["text"])
                except json.JSONDecodeError:
                    continue

                if payload.get("type") == "stop":
                    state = manager.get_session(session_id)
                    if state.audio_buffer.size > 0:
                        text = stt.transcribe(state.audio_buffer, partial=False)
                        if text:
                            state.confirmed_transcript = f"{state.confirmed_transcript} {text}".strip()
                        state.audio_buffer = np.empty(0, dtype=np.float32)

                    await manager.send_transcript(session_id, state.confirmed_transcript, is_final=True)
                    logger.info(f"Session {session_id} finalized transcript.")

    except WebSocketDisconnect:
        logger.info(f"Session {session_id} disconnected by client.")
    except Exception as e:
        logger.exception(f"Error in session {session_id}: {e}")
        await manager.send_error(session_id, "Internal transcription error.")
    finally:
        manager.disconnect(session_id)