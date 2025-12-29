#!/bin/bash

# Script pour créer les fichiers principaux du projet avec du contenu minimal mais fonctionnel

echo "Création des fichiers du projet Detection System..."

# Scripts
mkdir -p scripts
chmod +x scripts/*.sh 2>/dev/null || true

cat > scripts/setup.sh << 'EOF'
#!/bin/bash
echo "🚀 Setting up Detection System..."
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
mkdir -p keys logs tmp/uploads
echo "✅ Setup complete!"
EOF

cat > scripts/test.sh << 'EOF'
#!/bin/bash
echo "🧪 Running tests..."
pytest tests/ -v
EOF

cat > scripts/deploy.sh << 'EOF'
#!/bin/bash
echo "🚀 Deploying Detection System..."
docker-compose -f docker/docker-compose.yml up -d
EOF

chmod +x scripts/*.sh

# Docker files
cat > docker/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

cat > docker/docker-compose.yml << 'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:14-alpine
    environment:
      POSTGRES_DB: detection_db
      POSTGRES_USER: detector
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-password}
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/var/lib/redis

  api:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    environment:
      DATABASE_URL: postgresql://detector:${POSTGRES_PASSWORD:-password}@postgres:5432/detection_db
      REDIS_URL: redis://redis:6379/0

volumes:
  postgres_data:
  redis_data:
EOF

# Documentation
cat > docs/DEPLOYMENT.md << 'EOF'
# Deployment Guide

## Docker Deployment

```bash
./scripts/deploy.sh
```

## Manual Deployment

```bash
./scripts/setup.sh
python api/main.py
```

See full documentation in the project files.
EOF

cat > docs/API.md << 'EOF'
# API Documentation

Available at: http://localhost:8000/docs

## Endpoints

- POST /auth/login - Authentication
- POST /detect/ - Image detection
- GET /health - Health check

See OpenAPI documentation for complete API reference.
EOF

# CI/CD
mkdir -p .github/workflows
cat > .github/workflows/ci.yml << 'EOF'
name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest tests/
EOF

echo "✅ Tous les fichiers de configuration créés!"

