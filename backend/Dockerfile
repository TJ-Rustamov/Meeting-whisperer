FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN python -m pip install --no-cache-dir --upgrade pip setuptools wheel
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY app /app/app
COPY tests /app/tests

ENV DATA_DIR=/app/data
ENV AUDIO_DIR=/app/data/audio
ENV DATABASE_URL=sqlite:////app/data/meetings.db
ENV WHISPER_MODEL_PATH=/models/faster-whisper-base.en
ENV WHISPER_LANGUAGE=en
ENV WS_SAMPLE_RATE=16000
ENV SILERO_THRESHOLD=0.35

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
