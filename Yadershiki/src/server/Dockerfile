# образ node.js
FROM node:18-alpine

# рабочая директория
WORKDIR /app

# Копируем package.json и package-lock.json для установки зависимостей
COPY package*.json ./

# Устанавливаем зависимости
RUN npm install --production

# копируем весь исходный код в контейнер
COPY . .

# Порт где будет сервер
EXPOSE 8080

# запуск сервера
CMD ["node", "server.js"]