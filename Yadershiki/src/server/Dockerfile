FROM node:18-alpine

WORKDIR /app

# Копируем package.json отдельно для кэширования
COPY package*.json ./
RUN npm install

# Копируем исходный код
COPY . .

# Устанавливаем переменные окружения для логирования
ENV NODE_ENV=production
ENV LOG_LEVEL=info

# Используем stdout/stderr для логов (Docker best practice)
CMD ["node", "--enable-source-maps", "server.js"]