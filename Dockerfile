# Stage 1: Build Frontend
FROM node:20-slim AS frontend-builder
WORKDIR /frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Stage 2: Final Image
FROM python:3.12-slim
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY backend ./backend

# Copy built frontend to backend static directory
# main.py looks for "static" relative to its own directory
COPY --from=frontend-builder /frontend/dist ./backend/static

# Create uploads directory
RUN mkdir -p backend/uploads

# Expose port
EXPOSE 8000

# Run
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
