"""
prescription_service.py
-------------------------
PLACEHOLDER module for future AI-powered clinical processing on top of
the finalized doctor transcript: prescription generation, diagnosis
extraction, structured record creation, etc.

This module is intentionally decoupled from the live STT pipeline.
Once routes.py finalizes a transcript (the {"type": "final"} message
sent to the client), that plain string can be handed to any of the
functions below from a separate HTTP endpoint or background job.
None of this is wired into the WebSocket flow yet -- that is a
deliberate "future extension point" so the STT module can ship and be
used independently, then connected to AI processing later without
touching the transcription code.

Swap in your provider of choice (OpenAI, Gemini, or a local Llama
model via Ollama/vLLM) inside each function body below.
"""

from typing import List, TypedDict


class PrescriptionResult(TypedDict):
    medications: List[str]
    diagnosis: str
    follow_up: str
    raw_notes: str


async def generate_prescription(transcript: str) -> PrescriptionResult:
    """
    TODO: Send `transcript` to an LLM (OpenAI GPT-4, Gemini, or a local
    Llama model) with a prompt instructing it to extract structured
    prescription data (medication name, dosage, frequency, duration).

    Example (OpenAI):
        from openai import OpenAI
        client = OpenAI(api_key="...")
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Extract prescriptions as JSON..."},
                {"role": "user", "content": transcript},
            ],
        )
        # parse response.choices[0].message.content as JSON

    Example (local Llama via Ollama):
        import requests
        requests.post("http://localhost:11434/api/generate", json={
            "model": "llama3",
            "prompt": f"Extract prescription details from: {transcript}",
        })
    """
    # Placeholder stub response -- replace with a real LLM call.
    return PrescriptionResult(
        medications=[],
        diagnosis="",
        follow_up="",
        raw_notes=transcript,
    )


async def extract_diagnosis(transcript: str) -> str:
    """
    TODO: Send `transcript` to an LLM to summarize/extract the likely
    diagnosis or clinical impression from the dictated notes.
    """
    return ""


async def save_to_records(patient_id: str, transcript: str, structured_data: dict) -> bool:
    """
    TODO: Persist the finalized transcript plus any structured AI output
    (prescription, diagnosis) into your existing EHR/database layer.
    This is where you would call your platform's existing
    patient-records service/repository.
    """
    return True
