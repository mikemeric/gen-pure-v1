# Image de base légère
FROM python:3.10-slim

# Répertoire de travail
WORKDIR /app

# Installation des dépendances système (pour PDF et Images)
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copie des munitions
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie du code source
COPY . .

# Création des zones de mémoire
RUN mkdir -p static/reports data

# Port d'écoute
EXPOSE 10000

# Lancement du QG
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "10000"]