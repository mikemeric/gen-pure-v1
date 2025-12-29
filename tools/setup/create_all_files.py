import os
from pathlib import Path

# Créer un dictionnaire avec tous les fichiers et leur contenu
# Format: chemin: contenu

files_content = {}

# Je vais créer les fichiers les plus importants et des placeholders pour les autres
# pour que la structure soit complète

# Configuration principale
files_content['requirements.txt'] = """# Core dependencies
fastapi==0.109.0
uvicorn[standard]==0.27.0
pydantic==2.5.3
pydantic-settings==2.1.0

# Authentication & Security
pyjwt[crypto]==2.8.0
bcrypt==4.1.2
cryptography==42.0.0
python-multipart==0.0.6

# Database
psycopg2-binary==2.9.9
sqlalchemy==2.0.25

# Cache & Queue
redis==5.0.1
pika==1.3.2

# Computer Vision
opencv-python==4.9.0.80
numpy==1.26.3
scikit-learn==1.4.0
scipy==1.11.4
pillow==10.2.0

# HTTP Client
httpx==0.26.0
requests==2.31.0

# Development
pytest==7.4.4
pytest-cov==4.1.0
pytest-asyncio==0.23.3
black==24.1.1
flake8==7.0.0
isort==5.13.2
mypy==1.8.0
bandit==1.7.6
"""

files_content['.gitignore'] = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
ENV/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo

# Project specific
keys/*.key
keys/*.pem
.env
.env.*
!.env.example
logs/*.log
tmp/
*.db
*.sqlite

# Testing
.pytest_cache/
.coverage
htmlcov/
coverage.xml
*.cover

# Docker
*.tar.gz

# OS
.DS_Store
Thumbs.db
"""

files_content['.env.example'] = """# Environment
ENVIRONMENT=development

# API
API_PORT=8000
LOG_LEVEL=info

# Database
DATABASE_URL=postgresql://detector:password@localhost:5432/detection_db

# Redis
REDIS_URL=redis://localhost:6379/0

# RabbitMQ
RABBITMQ_URL=amqp://detector:password@localhost:5672/

# Security
JWT_SECRET_KEY=your-secret-key-here
MASTER_KEY_FILE=keys/master.key

# Detection
MAX_IO_WORKERS=4
MAX_CPU_WORKERS=4
"""

# Créer tous les fichiers
for filepath, content in files_content.items():
    full_path = Path(filepath)
    full_path.parent.mkdir(parents=True, exist_ok=True)
    full_path.write_text(content)
    print(f"Created: {filepath}")

print(f"\nTotal files created: {len(files_content)}")
