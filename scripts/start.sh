#!/bin/bash
set -e

# ==============================================================================
# FoodFlow AI — Single-Port Production Container Startup Script
# Manages FastAPI (8000), Streamlit (8501/8502), and Nginx Reverse Proxy ($PORT)
# ==============================================================================

echo "================================================================"
echo " Starting FoodFlow AI Production Container"
echo "================================================================"

# 1. Port Configuration
PORT="${PORT:-8501}"
FASTAPI_PORT="8000"

# If external PORT is 8501, shift internal Streamlit to 8502 to avoid collision
if [ "$PORT" = "8501" ]; then
    STREAMLIT_PORT="8502"
else
    STREAMLIT_PORT="8501"
fi

export PORT
export STREAMLIT_PORT
export FASTAPI_PORT
export FOODFLOW_API_URL="http://127.0.0.1:${FASTAPI_PORT}/api"

echo " Nginx Public Port:    ${PORT}"
echo " Streamlit Internal:   127.0.0.1:${STREAMLIT_PORT}"
echo " FastAPI Internal:     127.0.0.1:${FASTAPI_PORT}"
echo " Environment:          ${RENDER:+Render (RENDER=true)}${RENDER:-Local/Custom}"
echo "================================================================"

# 2. Configure Nginx
if [ -f /etc/nginx/nginx.conf.template ]; then
    echo "[start.sh] Generating /etc/nginx/nginx.conf from template..."
    sed -e "s/\${PORT}/${PORT}/g" \
        -e "s/\${STREAMLIT_PORT}/${STREAMLIT_PORT}/g" \
        /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf
elif [ -f nginx.conf.template ]; then
    echo "[start.sh] Generating /etc/nginx/nginx.conf from local template..."
    sed -e "s/\${PORT}/${PORT}/g" \
        -e "s/\${STREAMLIT_PORT}/${STREAMLIT_PORT}/g" \
        nginx.conf.template > /etc/nginx/nginx.conf
fi

echo "[start.sh] Validating Nginx configuration..."
nginx -t

# 3. Database Seed & QR Generation
echo "[start.sh] Initializing database and verifying seed data..."
python -m backend.seed || echo "[start.sh] Seed reported an error or already seeded; continuing."

echo "[start.sh] Generating counter QR code poster..."
python scripts/generate_qr.py || echo "[start.sh] QR generation warning; continuing."

# 4. Graceful Shutdown Signal Handler
cleanup() {
    echo ""
    echo "[start.sh] Received termination signal. Shutting down all processes..."
    kill -TERM "$FASTAPI_PID" "$STREAMLIT_PID" "$NGINX_PID" 2>/dev/null || true
    wait "$FASTAPI_PID" "$STREAMLIT_PID" "$NGINX_PID" 2>/dev/null || true
    echo "[start.sh] Clean shutdown complete."
    exit 0
}
trap cleanup SIGINT SIGTERM

# 5. Start FastAPI Backend (port 8000)
echo "[start.sh] Launching FastAPI backend on 127.0.0.1:${FASTAPI_PORT}..."
python -m uvicorn backend.main:app \
    --host 127.0.0.1 \
    --port "${FASTAPI_PORT}" \
    --log-level info &
FASTAPI_PID=$!

# 6. Start Streamlit Operator Dashboard
echo "[start.sh] Launching Streamlit dashboard on 127.0.0.1:${STREAMLIT_PORT}..."
python -m streamlit run dashboard/app.py \
    --server.address 127.0.0.1 \
    --server.port "${STREAMLIT_PORT}" \
    --server.headless true &
STREAMLIT_PID=$!

# Wait briefly for backends to begin listening
sleep 2

# 7. Start Nginx Reverse Proxy
echo "[start.sh] Starting Nginx reverse proxy on port ${PORT}..."
nginx -g "daemon off;" &
NGINX_PID=$!

echo "[start.sh] All processes active. Forwarding public port ${PORT} to internal services."

# Wait for any process to exit; if one dies, terminate container so orchestrator restarts it
wait -n "$FASTAPI_PID" "$STREAMLIT_PID" "$NGINX_PID"
cleanup
