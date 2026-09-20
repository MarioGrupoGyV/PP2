FROM node:22-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_API_URL=http://localhost:8000
ARG VITE_DATASET_NOTICE="Datos simulados de demostración"
ENV VITE_API_URL=$VITE_API_URL
ENV VITE_DATASET_NOTICE=$VITE_DATASET_NOTICE

RUN npm run build

FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
