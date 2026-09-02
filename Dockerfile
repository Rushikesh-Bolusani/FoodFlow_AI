FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        ffmpeg \
        libsm6 \
        libxext6 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt

COPY backend ./backend
COPY dashboard ./dashboard
COPY forecasting ./forecasting
COPY feedback_form ./feedback_form
COPY scripts ./scripts
COPY runs ./runs
COPY yolov8n.pt ./yolov8n.pt

ENV PYTHONUNBUFFERED=1
ENV FOODFLOW_API_URL=http://127.0.0.1:8000/api

EXPOSE 8000 8501

CMD ["python", "scripts/start_app.py"]
