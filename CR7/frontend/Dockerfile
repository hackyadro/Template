# Билд приложения
FROM node:22 AS build

WORKDIR /app
COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# Запуск через production-сервер
FROM node:22
WORKDIR /app

COPY --from=build /app ./

EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]
