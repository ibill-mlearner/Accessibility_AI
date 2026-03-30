# syntax=docker/dockerfile:1.7

FROM node:20-alpine AS frontend-dev

WORKDIR /app/AccessAppFront

COPY AccessAppFront/package*.json ./
RUN npm ci

COPY AccessAppFront .
RUN chown -R node:node /app
USER node

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]


FROM node:20-alpine AS frontend-build

WORKDIR /app/AccessAppFront

COPY AccessAppFront/package*.json ./
RUN npm ci

COPY AccessAppFront .
RUN chown -R node:node /app
USER node
RUN npm run build


FROM nginx:1.27-alpine AS frontend-prod

COPY --from=frontend-build /app/AccessAppFront/dist /usr/share/nginx/html

EXPOSE 80
