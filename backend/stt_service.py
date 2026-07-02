"""
stt_service.py
----------------
Wraps Faster-Whisper for speech-to-text. The model is loaded ONCE
(as a singleton) during FastAPI startup and reused across every
WebSocket session. This keeps memory usage low and avoids the
multi-second cold-start cost of reloading model weights per request.

NOTE ON "STREAMING":
Whisper (and therefore Faster-Whisper) is not a token-by-token streaming
ASR model like some specialized streaming engines. It transcribes a
window of audio at a time. To get a live, Google-Docs-Voice-Typing-like
experience, this module uses a "chunked re-transcription" strategy
(implemented in routes.py / websocket_manager.py):

  1. Incoming audio is buffered per session.
  2. Every PARTIAL_INTERVAL_SECONDS of new audio, a fast transcription
     pass (beam_size=1, no conditioning on previous text) runs over the
     buffered audio and is emitted as a "partial" result.
  3. When the buffer crosses MAX_BUFFER_SECONDS (or the doctor stops
     recording), a more accurate pass confirms the segment, appends it
     to the running transcript, and clears the buffer.

This keeps the UI feeling "live" while keeping inference cost and
memory bounded -- the buffer never grows unboundedly even on a long
dictation.
"""

import logging
from typing import Optional

import numpy as np
from faster_whisper import WhisperModel

logger = logging.getLogger("stt_service")

# ---------------------------------------------------------------------------
# Model configuration. Tune these for your deployment hardware.
# ---------------------------------------------------------------------------
MODEL_SIZE = "small"        # tiny / base / small / medium / large-v3
DEVICE = "cpu"               # use "cuda" if a GPU is available
COMPUTE_TYPE = "int8"        # int8 is CPU-friendly; use "float16" on GPU

SAMPLE_RATE = 16000           # Whisper expects 16kHz mono audio


class STTService:
    """
    Singleton wrapper around a single Faster-Whisper model instance.
    Call `STTService.load()` once at server startup (see main.py's
    lifespan handler) and `STTService.get()` everywhere else.
    """

    _instance: Optional["STTService"] = None

    def __init__(self):
        if STTService._instance is not None:
            raise RuntimeError(
                "STTService is a singleton -- use STTService.load()/get(), "
                "never instantiate it directly."
            )
        logger.info(
            f"Loading Faster-Whisper model '{MODEL_SIZE}' on {DEVICE} "
            f"({COMPUTE_TYPE})..."
        )
        self.model = WhisperModel(MODEL_SIZE, device=DEVICE, compute_type=COMPUTE_TYPE)
        logger.info("Faster-Whisper model loaded successfully.")

    @classmethod
    def load(cls) -> "STTService":
        """Load the model once. Safe to call multiple times (idempotent)."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def get(cls) -> "STTService":
        """Retrieve the already-loaded model instance."""
        if cls._instance is None:
            raise RuntimeError(
                "STTService not loaded yet. Call STTService.load() at startup."
            )
        return cls._instance

    def transcribe(self, audio: np.ndarray, partial: bool = False) -> str:
        """
        Transcribe a numpy float32 mono audio buffer (16kHz, range [-1, 1]).

        partial=True  -> optimized for speed (greedy decoding, beam_size=1),
                          used for the live/interim transcript while the
                          doctor is still speaking.
        partial=False -> optimized for accuracy (larger beam), used to
                          confirm a finished segment or the final
                          transcript when recording stops.
        """
        if audio.size == 0:
            return ""

        beam_size = 1 if partial else 5
        segments, _info = self.model.transcribe(
            audio,
            language="en",
            beam_size=beam_size,
            vad_filter=False,
            # vad_parameters=dict(min_silence_duration_ms=500),
            condition_on_previous_text=False,
        )
        text = " ".join(seg.text.strip() for seg in segments)
        return text.strip()
