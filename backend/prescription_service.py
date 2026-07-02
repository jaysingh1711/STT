"""
prescription_service.py
-------------------------
Converts a finalized doctor transcript into structured clinical data
using a LOCAL LLM via Ollama.
"""

import json
import logging
from typing import List, TypedDict

import httpx

logger = logging.getLogger("prescription_service")

OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "llama3.2"
REQUEST_TIMEOUT_SECONDS = 60.0

VALID_TIMING_SLOTS = ["Morning", "Afternoon", "Evening", "Night"]


class Medication(TypedDict):
    name: str
    dosage: str
    frequency: str
    duration: str
    timing: List[str]


class PrescriptionResult(TypedDict):
    medications: List[Medication]
    diagnosis: str
    follow_up: str
    raw_notes: str


_EXTRACTION_PROMPT = """You are a clinical documentation assistant. Extract structured information from the doctor's dictated notes below.

Return ONLY valid JSON, no extra commentary, in exactly this shape:
{{
  "medications": [
    {{"name": "", "dosage": "", "frequency": "", "duration": "", "timing": []}}
  ],
  "diagnosis": "",
  "follow_up": ""
}}

Rules:
- Only include information the doctor explicitly said. Never invent or infer.
- "frequency" should describe HOW OFTEN or the pattern (e.g. "twice a day", "every 6 hours", "as needed") -- do NOT repeat specific times of day here if "timing" already captures them.
- "timing" must be an array containing only values from this exact list: ["Morning", "Afternoon", "Evening", "Night"].
- If the doctor named specific times of day (e.g. "morning and evening"), put ONLY the count/pattern in "frequency" (e.g. "twice a day") and put the actual times in "timing" (e.g. ["Morning", "Evening"]). Do not duplicate the time names in both fields.
- If the doctor only said a count without naming specific times (e.g. "three times a day"), leave "timing" as an empty list [] -- do NOT guess or fill in any timing slots.
- "diagnosis" should be ONLY the clinical impression or disease name the doctor stated. Do NOT include medication instructions, frequency, or duration in diagnosis.
- "follow_up" should be ONLY explicit follow-up instructions (e.g. "come back in one week"). Do NOT put medication frequency or duration here. If no follow-up was mentioned, use "".
- Medication dosage, frequency and duration belong ONLY in the medications array, never in diagnosis or follow_up.
- If a field was not mentioned, use "" (or [] for medications/timing).

EXAMPLE:
Doctor's notes: "patient has fever and sore throat, diagnosis is viral pharyngitis, prescribe amoxicillin 500mg three times a day for 7 days, morning afternoon and evening, advise rest and fluids, follow up in one week"

Correct output:
{{
  "medications": [
    {{"name": "amoxicillin", "dosage": "500mg", "frequency": "three times a day", "duration": "7 days", "timing": ["Morning", "Afternoon", "Evening"]}}
  ],
  "diagnosis": "viral pharyngitis",
  "follow_up": "one week"
}}

Doctor's notes:
\"\"\"{transcript}\"\"\"
"""


def _sanitize_timing(timing_list) -> List[str]:
    if not isinstance(timing_list, list):
        return []
    return [slot for slot in VALID_TIMING_SLOTS if slot in timing_list]


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
        raise RuntimeError(
            "Could not reach the local AI model (Ollama). Make sure Ollama is "
            f"installed and running, and that you've pulled the model with 'ollama pull {OLLAMA_MODEL}'."
        ) from e
    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"Ollama returned an error: {e}") from e

    raw_text = payload.get("response", "")
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        logger.warning(f"Model did not return valid JSON: {raw_text[:200]}")
        parsed = {}

    medications = parsed.get("medications", []) or []
    for med in medications:
        med["timing"] = _sanitize_timing(med.get("timing", []))

    return PrescriptionResult(
        medications=medications,
        diagnosis=parsed.get("diagnosis", "") or "",
        follow_up=parsed.get("follow_up", "") or "",
        raw_notes=transcript,
    )


async def extract_diagnosis(transcript: str) -> str:
    result = await generate_prescription(transcript)
    return result["diagnosis"]


async def save_to_records(patient_id: str, transcript: str, structured_data: dict) -> bool:
    return True