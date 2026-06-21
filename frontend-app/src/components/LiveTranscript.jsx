import React, { useState } from "react";
import { API_BASE_URL } from "../services/websocketService";

function emptyMedication() {
  return { name: "", dosage: "", frequency: "", duration: "" };
}

export default function LiveTranscript({ liveText, finalText, isRecording }) {
  const [prescription, setPrescription] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [genError, setGenError] = useState(null);

  const handleGeneratePrescription = async () => {
    setIsGenerating(true);
    setGenError(null);
    try {
      const res = await fetch(`${API_BASE_URL}/generate-prescription`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ transcript: finalText }),
      });
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || "Request failed");
      }
      const data = await res.json();
      setPrescription({
        medications: data.medications?.length ? data.medications : [emptyMedication()],
        diagnosis: data.diagnosis || "",
        follow_up: data.follow_up || "",
      });
    } catch (err) {
      setGenError(err.message || "Could not generate prescription.");
    } finally {
      setIsGenerating(false);
    }
  };

  const updateMedication = (index, field, value) => {
    setPrescription((prev) => {
      const medications = [...prev.medications];
      medications[index] = { ...medications[index], [field]: value };
      return { ...prev, medications };
    });
  };

  const addMedication = () => {
    setPrescription((prev) => ({ ...prev, medications: [...prev.medications, emptyMedication()] }));
  };

  const removeMedication = (index) => {
    setPrescription((prev) => ({
      ...prev,
      medications: prev.medications.filter((_, i) => i !== index),
    }));
  };

  return (
    <div className="panel">
      <div className="panel-header">
        <h3>
          Live transcript
          <span className="ai-pill">Whisper AI</span>
        </h3>
        {isRecording && <span className="live-badge">LIVE</span>}
      </div>
      <div className="panel-body live-text">
        {liveText ? (
          <>
            {liveText}
            {isRecording && <span className="blinking-cursor" aria-hidden="true" />}
          </>
        ) : (
          <span className="placeholder">Transcript will appear here as you speak...</span>
        )}
      </div>

      {finalText && (
        <div className="panel final-notes">
          <div className="panel-header">
            <h3>Final doctor notes</h3>
            <button className="btn btn-copy" onClick={() => navigator.clipboard.writeText(finalText)}>
              Copy
            </button>
          </div>
          <div className="panel-body">{finalText}</div>

          <div className="ai-actions">
            <span className="ai-actions-label">AI actions</span>
            <button className="btn btn-ghost" onClick={handleGeneratePrescription} disabled={isGenerating}>
              {isGenerating ? "Generating..." : "Generate prescription"}
            </button>
            <button className="btn btn-ghost" disabled>Save to records</button>
          </div>

          {genError && (
            <div className="ai-error">
              {genError} Make sure Ollama is running locally (<code>ollama serve</code>) with the model pulled.
            </div>
          )}

          {prescription && (
            <div className="prescription-result">
              <div className="prescription-result-header">
                <span className="ai-pill">AI draft &mdash; review before use</span>
              </div>

              <label className="field-label">Diagnosis</label>
              <textarea
                className="field-input"
                rows={2}
                value={prescription.diagnosis}
                onChange={(e) => setPrescription((p) => ({ ...p, diagnosis: e.target.value }))}
              />

              <label className="field-label">Medications</label>
              {prescription.medications.map((med, i) => (
                <div className="medication-row" key={i}>
                  <input
                    className="field-input"
                    placeholder="Name"
                    value={med.name}
                    onChange={(e) => updateMedication(i, "name", e.target.value)}
                  />
                  <input
                    className="field-input"
                    placeholder="Dosage"
                    value={med.dosage}
                    onChange={(e) => updateMedication(i, "dosage", e.target.value)}
                  />
                  <input
                    className="field-input"
                    placeholder="Frequency"
                    value={med.frequency}
                    onChange={(e) => updateMedication(i, "frequency", e.target.value)}
                  />
                  <input
                    className="field-input"
                    placeholder="Duration"
                    value={med.duration}
                    onChange={(e) => updateMedication(i, "duration", e.target.value)}
                  />
                  <button
                    className="btn-remove-row"
                    onClick={() => removeMedication(i)}
                    aria-label="Remove medication"
                    type="button"
                  >
                    &times;
                  </button>
                </div>
              ))}
              <button className="btn btn-ghost btn-add-row" onClick={addMedication} type="button">
                + Add medication
              </button>

              <label className="field-label">Follow-up</label>
              <textarea
                className="field-input"
                rows={2}
                value={prescription.follow_up}
                onChange={(e) => setPrescription((p) => ({ ...p, follow_up: e.target.value }))}
              />
            </div>
          )}
        </div>
      )}
    </div>
  );
}