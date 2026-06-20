# MediScribe Voice-to-Notes

Real-time speech-to-text module for clinical dictation. A doctor clicks
**Start Recording**, speaks, sees a live transcript update as they talk,
clicks **Stop Recording**, and gets back a finalized transcript ready to
hand off to prescription/diagnosis-extraction AI or your EHR.

## Folder structure

```
mediscribe-stt/
├── backend/
│   ├── main.py                 # FastAPI app, loads model once at startup
│   ├── routes.py                # WS /ws/transcribe endpoint
│   ├── websocket_manager.py     # per-session connection + buffer state
│   ├── stt_service.py           # Faster-Whisper singleton wrapper
│   ├── prescription_service.py  # placeholder for future LLM extraction
│   └── requirements.txt
└── frontend/
    ├── components/
    │   ├── Recorder.jsx         # mic capture + Start/Stop UI
    │   └── LiveTranscript.jsx   # live + final transcript display
    ├── services/
    │   └── websocketService.js  # WebSocket client wrapper
    ├── App.jsx                  # wires everything together
    ├── App.css                  # dashboard styling
    └── package.json
```

## Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Frontend

If you're starting fresh:

```bash
npx create-react-app frontend-app
cd frontend-app
# copy components/, services/, App.jsx, App.css from this project into src/
npm install
```

If you're integrating into an **existing** React app, skip this and see
"Integrating into an existing app" below.

## Run

### Backend

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

The model loads once on startup -- you'll see a log line confirming it
before the server starts accepting connections.

### Frontend

```bash
cd frontend-app   # or wherever App.jsx lives
npm start
```

By default the frontend connects to `ws://localhost:8000/ws/transcribe`.
To point at a different backend host, set an environment variable before
building/running:

```bash
REACT_APP_STT_WS_HOST=your-api-host:8000 npm start
```

## Integrating into an existing React application

1. Copy `components/Recorder.jsx`, `components/LiveTranscript.jsx`, and
   `services/websocketService.js` into your existing `src/` tree.
2. Either reuse `App.jsx` as a standalone route/page, or copy its
   state-management logic (the `useState`/`useCallback` hooks) into
   wherever you want the dictation panel to live -- e.g. a modal inside
   a patient encounter screen.
3. Copy `App.css` (or merge its classes into your existing stylesheet --
   everything is scoped under `.mediscribe-app` so it won't leak).
4. Set `REACT_APP_STT_WS_HOST` to point at your FastAPI backend.
5. On the backend, mount `routes.py`'s router into your existing FastAPI
   app (or run it as a standalone microservice) and call `STTService.load()`
   once during your app's startup/lifespan handler.
6. When you're ready to wire up AI processing, expose
   `prescription_service.py`'s functions via a new HTTP endpoint (e.g.
   `POST /generate-prescription`) and call it from `LiveTranscript.jsx`'s
   "Generate Prescription" button using the finalized transcript.

## Notes on accuracy/latency tuning

- `MODEL_SIZE` in `stt_service.py` controls the accuracy/speed trade-off
  (`tiny`/`base`/`small`/`medium`/`large-v3`). `small` on CPU is a
  reasonable default for clinical dictation; move to `medium` + GPU for
  higher accuracy.
- `PARTIAL_INTERVAL_SECONDS` in `websocket_manager.py` controls how often
  the live transcript updates. Lower = more "live" feel, higher CPU load.
- `MAX_BUFFER_SECONDS` in `routes.py` bounds how long a single
  re-transcription pass can grow before being forced to a segment
  boundary, which keeps memory and latency predictable on long dictations.
