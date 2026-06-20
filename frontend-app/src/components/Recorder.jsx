/**
 * Recorder.jsx
 * -------------
 * Captures microphone audio, downsamples/converts it to 16-bit PCM
 * mono @ 16kHz (the format Faster-Whisper / the backend expects), and
 * streams it over the WebSocket in small chunks while recording.
 *
 * This component owns only the audio plumbing + Start/Stop UI. All
 * transcript state lives in App.jsx so this component can be dropped
 * into an existing dashboard with minimal wiring.
 */

import React, { useRef, useState, useCallback } from "react";

const TARGET_SAMPLE_RATE = 16000;

// Downsample a Float32Array audio buffer from its native sample rate
// down to 16kHz (what Whisper expects). Simple linear interpolation --
// good enough for speech; swap for a proper resampler library if you
// need higher fidelity.
function downsampleTo16k(buffer, inputSampleRate) {
  if (inputSampleRate === TARGET_SAMPLE_RATE) return buffer;
  const ratio = inputSampleRate / TARGET_SAMPLE_RATE;
  const newLength = Math.round(buffer.length / ratio);
  const result = new Float32Array(newLength);
  for (let i = 0; i < newLength; i++) {
    result[i] = buffer[Math.floor(i * ratio)];
  }
  return result;
}

function floatTo16BitPCM(float32Array) {
  const buffer = new ArrayBuffer(float32Array.length * 2);
  const view = new DataView(buffer);
  for (let i = 0; i < float32Array.length; i++) {
    const s = Math.max(-1, Math.min(1, float32Array[i]));
    view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return buffer;
}

export default function Recorder({ onAudioChunk, onStart, onStop, disabled }) {
  const [isRecording, setIsRecording] = useState(false);
  const audioContextRef = useRef(null);
  const processorRef = useRef(null);
  const sourceRef = useRef(null);
  const streamRef = useRef(null);

  const startRecording = useCallback(async () => {
    let stream;
    let audioContext;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      if (onStart) {
        await onStart();
      }

      streamRef.current = stream;
      audioContext = new (window.AudioContext || window.webkitAudioContext)();
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      sourceRef.current = source;

      // NOTE: ScriptProcessorNode is deprecated but still universally
      // supported and the simplest option for a drop-in module. For a
      // greenfield build, migrate this to an AudioWorkletProcessor.
      const bufferSize = 4096;
      const processor = audioContext.createScriptProcessor(bufferSize, 1, 1);
      processorRef.current = processor;

      processor.onaudioprocess = (event) => {
        const inputData = event.inputBuffer.getChannelData(0);
        const downsampled = downsampleTo16k(inputData, audioContext.sampleRate);
        const pcm16 = floatTo16BitPCM(downsampled);
        onAudioChunk(pcm16);
      };

      source.connect(processor);
      processor.connect(audioContext.destination);

      setIsRecording(true);
    } catch (err) {
      console.error("Start recording failed:", err);
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
      if (audioContext) {
        audioContext.close();
      }
      alert("Failed to start recording. Please make sure the backend server is running and microphone permissions are granted.");
    }
  }, [onAudioChunk, onStart]);

  const stopRecording = useCallback(() => {
    processorRef.current?.disconnect();
    sourceRef.current?.disconnect();
    audioContextRef.current?.close();
    streamRef.current?.getTracks().forEach((track) => track.stop());

    setIsRecording(false);
    onStop && onStop();
  }, [onStop]);

  return (
    <div className="recorder-controls">
      <button
        className="btn btn-start"
        onClick={startRecording}
        disabled={disabled || isRecording}
      >
        🎙️ Start Recording
      </button>
      <button
        className="btn btn-stop"
        onClick={stopRecording}
        disabled={disabled || !isRecording}
      >
        ⏹ Stop Recording
      </button>

      {isRecording && (
        <span className="status-badge recording">
          <span className="waveform" aria-hidden="true">
            <span></span><span></span><span></span><span></span><span></span>
          </span>
          RECORDING
        </span>
      )}
    </div>
  );
}
