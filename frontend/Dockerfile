# Stage 1 — Build
FROM oven/bun:1 AS build

WORKDIR /app

COPY frontend/package.json ./
RUN bun install

COPY frontend/ .
RUN bun run build

# Stage 2 — Serve
FROM nginx:alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80