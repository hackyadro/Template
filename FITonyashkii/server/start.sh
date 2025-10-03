#!/usr/bin/env bash
set -euo pipefail

echo "Starting FITonyashkii container..."

# Serve frontend (public/) on port 2020 using Python http.server
FRONT_PORT=${FRONT_PORT:-2020}
WS_PORT=${WS_PORT:-3030}
UDP_PORT=${UDP_PORT:-9999}

echo "Launching static file server on port ${FRONT_PORT}"
python -m http.server "${FRONT_PORT}" --directory /app/public &
FRONT_PID=$!

# Start websocket/udp server
echo "Launching map server (websocket:${WS_PORT}, udp:${UDP_PORT})"
python /app/server/server.py &

echo "Container started: frontend:http://${HOSTNAME}:${FRONT_PORT} ws-port:${WS_PORT} udp-port:${UDP_PORT}" 
SERVER_PID=$!

trap 'echo "Stopping..."; kill $FRONT_PID $SERVER_PID 2>/dev/null || true' SIGINT SIGTERM

wait -n $FRONT_PID $SERVER_PID

echo "One of the processes exited, shutting down"
kill $FRONT_PID $SERVER_PID 2>/dev/null || true