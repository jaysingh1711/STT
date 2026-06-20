/**
 * LiveTranscript.jsx
 * --------------------
 * Displays the live (interim) transcript while the doctor is speaking,
 * and the finalized doctor notes once recording stops.
 */

import React from "react";

export default function LiveTranscript({ liveText, finalText, isRecording }) {
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

          {/* Future AI actions -- wired up once prescription_service.py
              is exposed via its own HTTP endpoint and called from here. */}
          <div className="ai-actions">
            <span className="ai-actions-label">AI actions (coming soon)</span>
            <button className="btn btn-ghost" disabled>Generate prescription</button>
            <button className="btn btn-ghost" disabled>Extract diagnosis</button>
            <button className="btn btn-ghost" disabled>Save to records</button>
          </div>
        </div>
      )}
    </div>
  );
}
