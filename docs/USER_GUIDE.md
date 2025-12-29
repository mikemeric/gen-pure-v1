# 📚 GUIDE UTILISATEUR - Detection System v3.0

**Version** : 3.0.0  
**Date** : Décembre 2024  
**Auteur** : Dr. Emeric Tchamdjio (DI-SOLUTIONS SARL)

---

## 📖 TABLE DES MATIÈRES

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Utilisation de l'API](#utilisation-de-lapi)
5. [Calibration](#calibration)
6. [Détection de Niveau](#détection-de-niveau)
7. [Historique et Statistiques](#historique-et-statistiques)
8. [Dépannage](#dépannage)

---

## 1. INTRODUCTION

### 1.1 Vue d'ensemble

Le Detection System v3.0 est un système de détection de niveau de carburant par vision par ordinateur (Computer Vision). Il utilise 4 algorithmes CV différents pour détecter avec précision le niveau de carburant dans des réservoirs à partir d'images.

**Fonctionnalités principales** :
- ✅ Détection automatique par CV (4 algorithmes)
- ✅ Calibration personnalisée par réservoir
- ✅ API REST complète
- ✅ Historique des détections
- ✅ Statistiques et rapports
- ✅ Authentification sécurisée

### 1.2 Architecture

```
┌──────────────┐
│  Client App  │
└──────┬───────┘
       │ HTTP/REST
       ↓
┌──────────────┐
│  API REST    │
│  (FastAPI)   │
└──────┬───────┘
       │
       ↓
┌──────────────┐     ┌──────────────┐
│  Detection   │────→│  Calibration │
│  Service     │     │  System      │
└──────────────┘     └──────────────┘
```

---

## 2. INSTALLATION

### 2.1 Prérequis

```bash
- Python 3.10+
- OpenCV 4.x
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optionnel)
```

### 2.2 Installation avec Docker (Recommandé)

```bash
# Cloner le projet
git clone https://github.com/your-org/detection-system.git
cd detection-system

# Configurer l'environnement
cp .env.example .env
# Éditer .env avec vos paramètres

# Démarrer les services
docker-compose -f docker/docker-compose.prod.yml up -d

# Vérifier le statut
curl http://localhost:8000/api/health
```

### 2.3 Installation Manuelle

```bash
# Créer environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer dépendances
pip install -r requirements.txt

# Initialiser la base de données
psql -U detector -d detection_db -f infrastructure/database/migrations/init.sql

# Démarrer l'API
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

---

## 3. CONFIGURATION

### 3.1 Variables d'Environnement

Fichier `.env` :

```bash
# Environment
ENVIRONMENT=production

# Database
DATABASE_URL=postgresql://detector:password@localhost:5432/detection_db

# Redis
REDIS_URL=redis://localhost:6379/0

# RabbitMQ
RABBITMQ_URL=amqp://guest:guest@localhost:5672/

# Security
JWT_SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-encryption-key-here

# API
API_PORT=8000
API_HOST=0.0.0.0
```

### 3.2 Génération des Clés

```bash
# Générer JWT secret
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Générer encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

---

## 4. UTILISATION DE L'API

### 4.1 Authentification

#### Obtenir un Token JWT

```bash
curl -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "your_username",
    "password": "your_password"
  }'

# Response:
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

#### Utiliser le Token

```bash
# Ajouter le token dans les headers
curl "http://localhost:8000/api/v2/detect/history" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### 4.2 Créer une API Key

```bash
curl -X POST "http://localhost:8000/api/auth/api-keys" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Production Key",
    "permissions": ["detect", "calibrate"],
    "expires_days": 365
  }'

# Response:
{
  "api_key": "sk_live_abc123...",
  "key_id": "key_xyz789"
}
```

---

## 5. CALIBRATION

### 5.1 Créer une Calibration

**Étape 1** : Préparer les Points de Calibration

Mesurez manuellement les positions Y (en pixels) pour différents niveaux :
- 0% (réservoir vide)
- 100% (réservoir plein)
- Points intermédiaires (optionnel)

**Étape 2** : Créer via API

```bash
curl -X POST "http://localhost:8000/api/calibrations" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Réservoir 50L",
    "image_height": 1080,
    "tank_capacity_ml": 50000.0,
    "calibration_type": "linear",
    "points": [
      {
        "pixel_y": 972,
        "percentage": 0
      },
      {
        "pixel_y": 108,
        "percentage": 100
      }
    ]
  }'

# Response:
{
  "id": "cal_abc123",
  "name": "Réservoir 50L",
  "is_calibrated": true,
  "num_points": 2
}
```

### 5.2 Lister les Calibrations

```bash
curl "http://localhost:8000/api/calibrations" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response:
{
  "calibrations": [
    {
      "id": "cal_abc123",
      "name": "Réservoir 50L",
      "calibration_type": "linear",
      "is_calibrated": true,
      "num_points": 2
    }
  ],
  "total": 1
}
```

### 5.3 Exporter une Calibration

```bash
curl "http://localhost:8000/api/calibrations/cal_abc123/export" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -o calibration_reservoir_50L.json
```

---

## 6. DÉTECTION DE NIVEAU

### 6.1 Détection Simple

```bash
curl -X POST "http://localhost:8000/api/v2/detect" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@/path/to/fuel_tank.jpg" \
  -F "method=ensemble" \
  -F "use_preprocessing=true"

# Response:
{
  "success": true,
  "niveau_percentage": 62.5,
  "niveau_ml": 31250.0,
  "confiance": 0.875,
  "methode_utilisee": "ensemble",
  "temps_traitement_ms": 342.5,
  "timestamp": "2024-12-14T10:30:00Z"
}
```

### 6.2 Méthodes de Détection

| Méthode | Description | Vitesse | Précision |
|---------|-------------|---------|-----------|
| **hough** | Hough Transform (lignes) | Rapide | Bonne |
| **clustering** | K-Means clustering | Moyenne | Moyenne |
| **edge** | Edge detection | Rapide | Bonne |
| **ensemble** | Combine les 3 | Lente | Excellente |

**Recommandation** : Utilisez `ensemble` pour la meilleure précision.

### 6.3 Avec Calibration Spécifique

```bash
curl -X POST "http://localhost:8000/api/v2/detect" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@fuel_tank.jpg" \
  -F "method=ensemble" \
  -F "calibration_id=cal_abc123"
```

---

## 7. HISTORIQUE ET STATISTIQUES

### 7.1 Consulter l'Historique

```bash
# Dernières 10 détections
curl "http://localhost:8000/api/v2/detect/history?skip=0&limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Filtrer par confiance minimale
curl "http://localhost:8000/api/v2/detect/history?min_confidence=0.7" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Filtrer par méthode
curl "http://localhost:8000/api/v2/detect/history?method=ensemble" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 7.2 Obtenir les Statistiques

```bash
curl "http://localhost:8000/api/v2/detect/statistics" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Response:
{
  "total_detections": 1250,
  "avg_confidence": 0.842,
  "avg_level": 58.3,
  "avg_processing_time_ms": 345.2,
  "methods_used": {
    "ensemble": 1050,
    "hough": 120,
    "clustering": 50,
    "edge": 30
  },
  "last_detection": "2024-12-14T15:30:00Z"
}
```

---

## 8. DÉPANNAGE

### 8.1 Problèmes Courants

#### Problème : "Authentication failed"

**Solution** :
```bash
# Vérifier que le token est valide
curl "http://localhost:8000/api/auth/verify" \
  -H "Authorization: Bearer YOUR_TOKEN"

# Si expiré, rafraîchir
curl -X POST "http://localhost:8000/api/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "YOUR_REFRESH_TOKEN"}'
```

#### Problème : "File too large"

**Solution** : Le système accepte des images jusqu'à 10MB. Réduisez la taille :
```bash
# Avec ImageMagick
convert input.jpg -resize 1920x1080 -quality 85 output.jpg
```

#### Problème : "Low confidence score"

**Causes possibles** :
- Image floue ou de mauvaise qualité
- Mauvais éclairage
- Calibration incorrecte

**Solution** :
1. Vérifier la qualité de l'image
2. Recalibrer avec des points précis
3. Essayer différentes méthodes de détection

### 8.2 Logs et Debugging

```bash
# Voir les logs Docker
docker-compose logs -f api

# Logs de l'application
tail -f logs/detection_system.log

# Mode debug (dans .env)
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

### 8.3 Support

Pour toute question ou problème :
- 📧 Email : support@di-solutions.cm
- 📞 Téléphone : +237 XXX XXX XXX
- 📖 Documentation : https://docs.di-solutions.cm

---

**© 2024 DI-SOLUTIONS SARL - Tous droits réservés**
