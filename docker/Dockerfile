FROM python:3.11-slim

WORKDIR /app

# Installation des d?pendances syst?me critiques
# libmagic1 : Pour la validation des fichiers
# libglib2.0-0 : Souvent requis par OpenCV m?me en headless
RUN apt-get update && apt-get install -y \
    libmagic1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
