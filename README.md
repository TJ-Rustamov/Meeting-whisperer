# Meeting Whisperer

Local-first meeting transcription platform with a React frontend and FastAPI backend.

## Repository Layout

- `frontend/`: web UI (Vite + React + TypeScript)
- `backend/`: API, realtime transcription pipeline, meeting storage
- `models/`: local STT model assets (Whisper-compatible CTranslate2 layout)

This root `README.md` is the canonical documentation for setup and configuration.

## Features

- Realtime meeting transcription
- Meeting list with playback and bulk delete
- Audio + optional screen video capture
- Post-processing/diarization pipeline (optional)
- Docker-first local deployment

## Requirements

- Docker + Docker Compose
- Optional: GitHub account and `gh` CLI for publishing

## Quick Start (Docker)

1. Copy env template:

```bash
cp .env.example .env
```

2. Set required keys in `.env`:

- `POSTPROCESS_HF_TOKEN` (required only if diarization via pyannote is enabled)

3. Start services:

```bash
docker compose up -d --build
```

4. Open app:

- Frontend: `http://localhost:5173`
- Backend health: `http://localhost:8000/health`

## Environment Variables

Use `.env.example` as baseline. Main groups:

- Core/runtime:
  `APP_NAME`, `LOG_LEVEL`, `DATABASE_URL`, `DATA_DIR`, `AUDIO_DIR`
- STT behavior:
  `WHISPER_*` values
- Realtime/VAD tuning:
  `WS_SAMPLE_RATE`, `SILERO_*`, `VAD_*`, `PARTIAL_*`, `SILENCE_FINALIZE_SEC`, `LIVE_OVERLAP_SEC`
- Post-processing:
  `POSTPROCESS_*`
- Frontend API (optional local override):
  `VITE_API_BASE_URL`

### What Users Can Safely Customize

- Accuracy/speed tradeoff: `WHISPER_BEAM_SIZE`, `WHISPER_BEST_OF`, `WHISPER_COMPUTE_TYPE`
- Responsiveness/latency: `PARTIAL_INTERVAL_SEC`, `SILENCE_FINALIZE_SEC`, `WS_MAX_UTTERANCE_SEC`
- Noise handling: `SILERO_THRESHOLD`, `VAD_MIN_RMS_FLOOR`, `VAD_QUIET_MULTIPLIER`
- Diarization strictness: `POSTPROCESS_RETRY_*`, `POSTPROCESS_FORCE_NUM_SPEAKERS`
- Logging verbosity: `LOG_LEVEL`

## Models

This repo keeps lightweight STT model metadata/assets only.

Not committed (by design):

- heavyweight model binaries (for example `model.bin`)
- TTS models

Expected runtime path:

- `models/faster-whisper-base.en/model.bin`

## Credits

STT stack and original model authors:

- OpenAI Whisper model authors:
  `openai/whisper-base.en` https://huggingface.co/openai/whisper-base.en
- SYSTRAN faster-whisper maintainers:
  https://github.com/SYSTRAN/faster-whisper
- OpenNMT CTranslate2:
  https://github.com/OpenNMT/CTranslate2
- pyannote.audio diarization tooling:
  https://github.com/pyannote/pyannote-audio

## Security / Secrets

- Never commit `.env`.
- Put secrets only in local `.env` (for example `POSTPROCESS_HF_TOKEN`).
- `.gitignore` is configured to exclude env files, local DB/media, build artifacts, and heavy model files.

## Publish to GitHub (Public)

From the repository root:

```bash
git init
git add .
git commit -m "Initial public release"
git branch -M main
git remote add origin https://github.com/<your-username>/meeting-whisperer.git
git push -u origin main
```

Or with GitHub CLI:

```bash
gh repo create meeting-whisperer --public --source . --remote origin --push
```

## License

This project is licensed under **Meeting Whisperer Personal Use License v1.0**.

- Personal and non-commercial use is allowed.
- Commercial use is **not allowed** without prior written permission from the author.

See [LICENSE](./LICENSE) for full terms.

Third-party dependencies and model assets retain their own licenses.
