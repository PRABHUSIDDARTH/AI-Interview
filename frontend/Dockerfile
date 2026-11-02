# Multi-stage production Dockerfile for Frontend (Vite + React)

# Stage 1: Build stage
FROM node:20-alpine as build-stage

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_API_BASE_URL
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build

# Stage 2: Serve stage
FROM nginx:alpine as production-stage

COPY --from=build-stage /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Install curl for healthcheck
RUN apk add --no-cache curl

EXPOSE 80

HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:80/nginx-health || exit 1

CMD ["nginx", "-g", "daemon off;"]
