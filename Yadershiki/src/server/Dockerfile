FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm install

COPY . .

ENV NODE_ENV=production
ENV LOG_LEVEL=info

CMD ["node", "--enable-source-maps", "server.js"]