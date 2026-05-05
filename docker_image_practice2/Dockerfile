FROM node:25-alpine3.22

COPY src /app/
COPY package.json /app/

WORKDIR /app

RUN npm install

CMD ["node", "server.js"]