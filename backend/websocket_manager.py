"""
websocket_manager.py
---------------------
Manages active doctor "dictation sessions" over WebSocket connections.
Each connected doctor session gets its own isolated audio buffer and
transcript state, so multiple doctors can dictate concurrently (e.g.
in different exam rooms / browser tabs) without interfering with
each other.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict

import numpy as np
from fastapi import WebSocket

from stt_service import SAMPLE_RATE

logger = logging.getLogger("websocket_manager")

# How many seconds of new audio to accumulate before running a "partial"
# transcription pass. Lower = more live-feeling, higher = less CPU usage.
PARTIAL_INTERVAL_SECONDS = 2.0


@dataclass
class SessionState:
    """Per-connection audio buffer and transcript state."""

    websocket: WebSocket
    audio_buffer: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.float32))
    confirmed_transcript: str = ""        # text already finalized for this session
    seconds_since_last_partial: float = 0.0


class WebSocketManager:
    """
    Tracks all active sessions (one per connected doctor/browser tab)
    and provides helpers to push partial/final transcripts back to the
    correct client.
    """

    def __init__(self):
        self.sessions: Dict[str, SessionState] = {}

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self.sessions[session_id] = SessionState(websocket=websocket)
        logger.info(f"Session {session_id} connected. Active sessions: {len(self.sessions)}")

    def disconnect(self, session_id: str) -> None:
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Session {session_id} disconnected. Active sessions: {len(self.sessions)}")

    def get_session(self, session_id: str) -> SessionState:
        return self.sessions[session_id]

    def append_audio(self, session_id: str, pcm_chunk: np.ndarray) -> None:
        """Append a new float32 PCM chunk to a session's rolling buffer."""
        state = self.sessions[session_id]
        state.audio_buffer = np.concatenate([state.audio_buffer, pcm_chunk])
        state.seconds_since_last_partial += len(pcm_chunk) / SAMPLE_RATE

    async def send_transcript(self, session_id: str, text: str, is_final: bool) -> None:
        """Push a transcript update down the WebSocket to the doctor's browser."""
        state = self.sessions.get(session_id)
        if not state:
            return
        try:
            await state.websocket.send_json({
                "type": "final" if is_final else "partial",
                "text": text,
            })
        except Exception as e:
            logger.warning(f"Failed to send transcript to session {session_id}: {e}")

    async def send_error(self, session_id: str, message: str) -> None:
        state = self.sessions.get(session_id)
        if not state:
            return
        try:
            await state.websocket.send_json({"type": "error", "message": message})
        except Exception:
            pass


# A single shared manager instance used across the app.
manager = WebSocketManager()
