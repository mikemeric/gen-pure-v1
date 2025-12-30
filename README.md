🛡️ GEN-PURE OMEGA : SYSTÈME DE DÉFENSE ET DE CONTRÔLE LOGISTIQUE

GEN-PURE OMEGA est une plateforme d'intelligence distribuée conçue pour garantir l'intégrité absolue des flux de carburant. Le système combine vision par ordinateur (OpenCV), Intelligence Artificielle générative (Gemini) et protocoles de sécurité cryptographique (JWT).



🎖️ ARCHITECTURE DES AGENTS

Le système est articulé autour de 7 unités d'élite :



SENTINELLE (fuel\_detector.py) : Analyse spectrale et détection d'eau libre.



ARCHIVISTE (memory\_unit.py) : Gestionnaire de la mémoire centrale et de l'historique.



LÉGISTE (legiste\_agent.py) : Certification officielle et génération de rapports PDF.



FLUX (flux\_agent.py) : Cartographie tactique et surveillance du réseau de stations.



GARDIEN (gardien\_agent.py) : Sécurité périmétrale, accès et signatures numériques.



SPECTRE (spectre\_agent.py) : Unité d'intervention rapide par alertes emails.



VISION (vision\_agent.py) : Analyse comparative et différentielle des rapports.



🚀 PROTOCOLE D'INSTALLATION

1\. Préparation du Magasin de Munitions

Assurez-vous d'avoir Python 3.10+ installé, puis déployez les dépendances :



Bash



pip install -r requirements.txt

2\. Configuration du Périmètre de Sécurité

Exécutez le script de configuration pour générer votre fichier .env :



Bash



python setup\_env.py

(Vous devrez fournir votre GOOGLE\_API\_KEY et vos identifiants SMTP pour l'Agent SPECTRE).



3\. Lancement du QG

Démarrez le serveur de commandement :



Bash



python main.py

Accédez à l'interface via : http://127.0.0.1:10000



🛠️ MODES OPÉRATIONNELS

📡 Unité Mobile (Smartphone)

Accédez à /scan depuis un terminal mobile. Le système active automatiquement la caméra arrière pour analyser l'échantillon. Un verdict immédiat est rendu et synchronisé avec le QG.



🏛️ Poste de Commandement (Dashboard)

Accédez à /manager pour superviser l'ensemble du territoire.



Alerte Réseau : L'Agent FLUX signale automatiquement toute anomalie systémique.



Mode Vision : Sélectionnez deux rapports dans le registre et cliquez sur "LANCER VISION" pour comparer l'évolution de la qualité.



🔐 CODES D'ACCÈS ÉTAT-MAJOR

Général en Chef : Idriss



Code OMEGA : OMEGA123



📁 STRUCTURE DU PROJET

Plaintext



GEN-PURE-OMEGA/

├── main.py                 # Coordonnateur Central

├── setup\_env.py            # Configuration Sécurité

├── requirements.txt        # Arsenal Logiciel

├── data/                   # Mémoire Centrale (JSON/SQL)

├── static/

│   └── reports/            # Archives PDF Certifiées

├── templates/              # Interfaces de Commandement

└── services/

&nbsp;   ├── detection/          # Unité Sentinelle

&nbsp;   ├── database/           # Unité Archiviste

&nbsp;   ├── reporting/          # Unité Légiste

&nbsp;   ├── security/           # Unité Gardien

&nbsp;   └── notifications/      # Unité Spectre

