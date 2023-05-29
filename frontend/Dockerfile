FROM node:14-alpine3.17

WORKDIR /app/frontend

COPY package*.json ./

RUN yarn install

COPY . .

# TODO change on production
CMD yarn serve
