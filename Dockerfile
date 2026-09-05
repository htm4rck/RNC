# Stage 1: Build frontend
FROM node:24-alpine AS frontend-build
ARG UI_PREFIX=/
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npx ng build --configuration production --base-href="${UI_PREFIX}"

# Stage 2: Production API + static frontend
FROM python:3.14-slim
WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

COPY backend/pyproject.toml ./backend/pyproject.toml
COPY backend/app ./backend/app
WORKDIR /app/backend
RUN pip install --no-cache-dir .

WORKDIR /app
COPY --from=frontend-build /app/frontend/dist/remote-career-navigator-web/browser ./public

EXPOSE 8050
CMD ["sh", "-c", "uvicorn app.main:app --app-dir /app/backend --host 0.0.0.0 --port ${PORT:-8050}"]
