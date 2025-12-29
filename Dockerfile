FROM python:3.9-slim

# On définit le dossier de travail
WORKDIR /app

# On installe les dépendances système pour PostgreSQL (souvent nécessaire pour psycopg2)
RUN apt-get update && apt-get install -y libpq-dev gcc && rm -rf /var/lib/apt/lists/*

# On copie tout le dossier (y compris api/, core/, etc.)
COPY . .

# On installe les librairies Python
RUN pip install --no-cache-dir -r requirements.txt

# La commande de démarrage spécifique à FastAPI sur Render
# Render fournit le port via la variable d'environnement $PORT
CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-10000}"]