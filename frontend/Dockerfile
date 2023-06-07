FROM node:lts-alpine as build-stage
WORKDIR /app

COPY package*.json ./
RUN yarn install
COPY . .
RUN yarn build

# production stage
FROM nginx:stable-alpine as production-stage
COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY default_nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080