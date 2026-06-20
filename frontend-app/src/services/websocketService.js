/**
 * websocketService.js
 * ---------------------
 * Thin wrapper around the native WebSocket API for the Voice-to-Notes
 * module. Handles connecting to the FastAPI /ws/transcribe endpoint,
 * sending binary PCM audio chunks, sending the "stop" control message,
 * and dispatching incoming partial/final transcript events to whoever
 * is listening (typically App.jsx).
 *
 * Kept framework-agnostic (no React imports) so it can be reused
 * outside this specific component tree if needed.
 */

const DEFAULT_WS_URL =
  (window.location.protocol === "https:" ? "wss://" : "ws://") +
  (process.env.REACT_APP_STT_WS_HOST || "localhost:8000") +
  "/ws/transcribe";

export class TranscriptionSocket {
  constructor({ url = DEFAULT_WS_URL, onPartial, onFinal, onError, onStatusChange } = {}) {
    this.url = url;
    this.onPartial = onPartial || (() => {});
    this.onFinal = onFinal || (() => {});
    this.onError = onError || (() => {});
    this.onStatusChange = onStatusChange || (() => {});
    this.socket = null;
  }

  connect() {
    return new Promise((resolve, reject) => {
      this.socket = new WebSocket(this.url);
      this.socket.binaryType = "arraybuffer";

      this.socket.onopen = () => {
        this.onStatusChange("connected");
        resolve();
      };

      this.socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "partial") {
            this.onPartial(data.text);
          } else if (data.type === "final") {
            this.onFinal(data.text);
          } else if (data.type === "error") {
            this.onError(data.message);
          }
        } catch (err) {
          console.error("Failed to parse transcript message:", err);
        }
      };

      this.socket.onerror = (err) => {
        this.onStatusChange("error");
        this.onError("WebSocket connection error.");
        reject(err);
      };

      this.socket.onclose = () => {
        this.onStatusChange("disconnected");
      };
    });
  }

  /** Send a raw audio chunk (ArrayBuffer of 16-bit PCM samples) to the server. */
  sendAudioChunk(chunk) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(chunk);
    }
  }

  /** Tell the server recording has stopped; triggers the final transcript. */
  sendStop() {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify({ type: "stop" }));
    }
  }

  close() {
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }
}
