# Используем официальный образ Node.js
FROM node:18-alpine

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем package.json и package-lock.json для установки зависимостей
COPY package*.json ./

# Устанавливаем зависимости
RUN npm install --production

# Копируем весь исходный код в контейнер
COPY . .

# Указываем порт, который будет использовать сервер
EXPOSE 8080

# Запускаем сервер
CMD ["node", "server.js"]
