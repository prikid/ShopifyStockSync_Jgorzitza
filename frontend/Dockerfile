# build stage
#FROM node:14-alpine3.17 as build-stage
#WORKDIR /app
#COPY package*.json ./
#RUN yarn install
#COPY . .
#RUN yarn build
#
## production stage
#FROM nginx:stable-alpine as production-stage
#COPY --from=build-stage /app/dist /usr/share/nginx/html
#EXPOSE 80
#CMD ["nginx", "-g", "daemon off;"]

FROM node:14-alpine3.17 as build-stage
RUN yarn global add http-server
WORKDIR /app
COPY package*.json ./
RUN yarn install
COPY . .
RUN yarn build

EXPOSE 8080
CMD [ "http-server", "dist" ]