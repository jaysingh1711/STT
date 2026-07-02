const STT_HOST = process.env.REACT_APP_STT_WS_HOST || "localhost:8000";

const DEFAULT_WS_URL =
  (window.location.protocol === "https:" ? "wss://" : "ws://") + STT_HOST + "/ws/transcribe";

export const API_BASE_URL = (window.location.protocol === "https:" ? "https://" : "http://") + STT_HOST;

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
      // Close AFTER final transcript received, not before
      setTimeout(() => this.close(), 500);
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

  sendAudioChunk(chunk) {
    if (this.socket && this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(chunk);
    }
  }

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