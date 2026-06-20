/**
 * App.jsx
 * --------
 * Top-level component wiring the Recorder, the WebSocket connection,
 * and the LiveTranscript display together. This is the piece you'd
 * mount inside an existing healthcare dashboard (e.g. as a route, or
 * a panel within a patient-encounter screen).
 */

import React, { useRef, useState, useCallback } from "react";
import Recorder from "./components/Recorder";
import LiveTranscript from "./components/LiveTranscript";
import { TranscriptionSocket } from "./services/websocketService";
import "./App.css";

export default function App() {
  const [liveText, setLiveText] = useState("");
  const [finalText, setFinalText] = useState("");
  const [isRecording, setIsRecording] = useState(false);
  const [connectionStatus, setConnectionStatus] = useState("idle");

  const socketRef = useRef(null);

  const handleStart = useCallback(async () => {
    setFinalText("");
    setLiveText("");

    const socket = new TranscriptionSocket({
      onPartial: (text) => setLiveText(text),
      onFinal: (text) => {
        setFinalText(text);
        setLiveText(text);
      },
      onError: (msg) => console.error("STT error:", msg),
      onStatusChange: (status) => setConnectionStatus(status),
    });

    try {
      await socket.connect();
      socketRef.current = socket;
      setIsRecording(true);
    } catch (err) {
      console.error("Failed to connect to transcription socket:", err);
      setConnectionStatus("error");
      setIsRecording(false);
      throw err;
    }
  }, []);

  const handleAudioChunk = useCallback((pcm16Buffer) => {
    socketRef.current?.sendAudioChunk(pcm16Buffer);
  }, []);

  const handleStop = useCallback(() => {
    socketRef.current?.sendStop();
    setIsRecording(false);
    // Give the server a moment to send back the final transcript
    // before closing the socket.
    setTimeout(() => socketRef.current?.close(), 1500);
  }, []);

  return (
    <div className="mediscribe-app">
      <header className="app-header">
        <div className="brand">
          <span className="brand-icon">⚕️</span>
          <span className="brand-name">MediScribe</span>
          <span className="brand-tag">AI Clinical Notes</span>
        </div>
        <span className={`session-badge ${connectionStatus}`}>
          {isRecording ? "Dr. Session Active" : "Idle"}
        </span>
      </header>

      <main className="app-main">
        <h1>Voice-to-Notes</h1>
        <p className="subtitle">
          Dictate patient observations and prescriptions. AI transcribes your notes live.
        </p>

        <Recorder onAudioChunk={handleAudioChunk} onStart={handleStart} onStop={handleStop} />

        <LiveTranscript liveText={liveText} finalText={finalText} isRecording={isRecording} />

        <p className="privacy-note">🔒 Audio processed locally. HIPAA-compliant architecture.</p>
      </main>
    </div>
  );
}
