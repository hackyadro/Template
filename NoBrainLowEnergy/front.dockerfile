# syntax=docker/dockerfile:1.6
ARG APP_DIR=src/front

########################
# Build stage
########################
FROM node:22-alpine3.22 AS build
ARG APP_DIR
WORKDIR /build

# Копируем только манифесты, чтобы кешировался npm ci
COPY ${APP_DIR}/package*.json ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund

# Копируем исходники и собираем
COPY ${APP_DIR}/ ./
# Если Vite: сборка в dist/
RUN npm run build

########################
# Runtime (nginx)
########################
FROM nginx:alpine AS runtime

# Статические файлы
COPY --from=build /build/dist/ /usr/share/nginx/html/

# SPA-фоллбек на index.html и кэш ассетов
RUN rm -f /etc/nginx/conf.d/default.conf && \
    printf '%s\n' \
    'server {' \
    '  listen 80; server_name _;' \
    '  root /usr/share/nginx/html; index index.html;' \
    '  location /assets/ { add_header Cache-Control "public, max-age=31536000, immutable"; }' \
    '  location / { try_files $uri $uri/ /index.html; }' \
    '}' > /etc/nginx/conf.d/app.conf

EXPOSE 80
