FROM python:3.11-slim

WORKDIR /app

ARG APP_USER=appuser
ENV PYTHONUNBUFFERED=1 \
    WS_PORT=3030 \
    FRONT_PORT=2020 \
    UDP_PORT=9999

# Install system deps (if later needed) and python deps first for better layer caching
COPY server/requirements.txt ./server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt \
    && useradd -m "$APP_USER"

# Copy project source
COPY . .

# Ensure start script is executable
RUN chmod +x server/start.sh \
    && chown -R $APP_USER:$APP_USER /app

# Expose the ports (frontend HTTP + websocket + UDP)
EXPOSE ${FRONT_PORT} ${WS_PORT} ${UDP_PORT}/udp

USER $APP_USER

CMD ["bash", "server/start.sh"]
