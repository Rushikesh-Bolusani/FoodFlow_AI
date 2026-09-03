FROM python:3.12-slim

WORKDIR /app

# Install system dependencies including Nginx reverse proxy and curl for health probes
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        ffmpeg \
        libsm6 \
        libxext6 \
        nginx \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements-web.txt .
RUN pip install --no-cache-dir -r requirements-web.txt

# Copy Nginx template and default configuration
COPY nginx.conf.template /etc/nginx/nginx.conf.template
COPY nginx.conf /etc/nginx/nginx.conf
COPY nginx.conf.template ./nginx.conf.template
COPY nginx.conf ./nginx.conf

# Copy application source directories
COPY backend ./backend
COPY dashboard ./dashboard
COPY forecasting ./forecasting
COPY feedback_form ./feedback_form
COPY scripts ./scripts
COPY runs ./runs
COPY yolov8n.pt ./yolov8n.pt

# Ensure startup scripts are executable
RUN chmod +x scripts/start.sh

ENV PYTHONUNBUFFERED=1
ENV FOODFLOW_API_URL=http://127.0.0.1:8000/api

# Expose primary port (Render maps to single port configured via $PORT, defaulting to 8501)
EXPOSE 8501 8000 8502

CMD ["/bin/bash", "scripts/start.sh"]
