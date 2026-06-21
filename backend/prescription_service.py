"""
prescription_service.py
-------------------------
Converts a finalized doctor transcript into structured clinical data
(medications, diagnosis, follow-up) using a LOCAL LLM via Ollama --
free, no API key, runs entirely on this machine.
"""

import json
import logging
from typing import List, TypedDict

import httpx

logger = logging.getLogger("prescription_service")

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2"
REQUEST_TIMEOUT_SECONDS = 60.0


class Medication(TypedDict):
    name: str
    dosage: str
    frequency: str
    duration: str


class PrescriptionResult(TypedDict):
    medications: List[Medication]
    diagnosis: str
    follow_up: str
    raw_notes: str


_EXTRACTION_PROMPT = """You are a clinical documentation assistant. Extract structured information from the doctor's dictated notes below.

Return ONLY valid JSON, no extra commentary, in exactly this shape:
{{
  "medications": [
    {{"name": "", "dosage": "", "frequency": "", "duration": ""}}
  ],
  "diagnosis": "",
  "follow_up": ""
}}

Rules:
- Only include a medication, dosage, or instruction if the doctor explicitly said it. Never invent or infer a dosage that was not stated.
- If a field was not mentioned, use an empty string "" (or an empty list [] for medications).
- "diagnosis" should be a short clinical impression in the doctor's own words, not a copy of the full transcript.
- "follow_up" should be any follow-up timing/instructions mentioned, or "" if none.

Doctor's notes:
\"\"\"{transcript}\"\"\"
"""


async def generate_prescription(transcript: str) -> PrescriptionResult:
    empty = PrescriptionResult(medications=[], diagnosis="", follow_up="", raw_notes=transcript)
    if not transcript.strip():
        return empty

    prompt = _EXTRACTION_PROMPT.format(transcript=transcript)

    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
            response = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.1},
                },
            )
            response.raise_for_status()
            payload = response.json()
    except httpx.ConnectError as e:
        logger.error("Could not reach Ollama -- is it running?")
        raise RuntimeError(
            "Could not reach the local AI model (Ollama). Make sure Ollama is "
            "installed and running, and that you've pulled the model with "
            f"'ollama pull {OLLAMA_MODEL}'."
        ) from e
    except httpx.HTTPStatusError as e:
        logger.error(f"Ollama returned an error: {e}")
        raise RuntimeError(f"Ollama returned an error: {e}") from e

    raw_text = payload.get("response", "")
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.warning(f"Model did not return valid JSON, got: {raw_text[:200]}")
        parsed = {}

    return PrescriptionResult(
        medications=parsed.get("medications", []) or [],
        diagnosis=parsed.get("diagnosis", "") or "",
        follow_up=parsed.get("follow_up", "") or "",
        raw_notes=transcript,
    )


async def extract_diagnosis(transcript: str) -> str:
    result = await generate_prescription(transcript)
    return result["diagnosis"]


async def save_to_records(patient_id: str, transcript: str, structured_data: dict) -> bool:
    # TODO: persist into your EHR/database layer -- not implemented yet.
    return True