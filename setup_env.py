import os

def initialize_omega_security():
    print("--- CONFIGURATION DU PÉRIMÈTRE DE SÉCURITÉ GEN-PURE ---")
    
    # 1. Clés de Chiffrement (Pour Agent GARDIEN)
    secret_key = input("Définissez votre Clé Secrète OMEGA (ex: SuperSecret2025) : ")
    
    # 2. Configuration Email (Pour Agent SPECTRE)
    email = input("Email d'expédition (Gmail) : ")
    email_pass = input("Mot de passe d'application Gmail (16 caractères) : ")
    admin_email = input("Email de réception de l'État-Major : ")

    env_content = f"""# --- CONFIGURATION SÉCURISÉE ---
SECRET_KEY={secret_key}
ALGORITHM=HS256

# --- CONFIGURATION NOTIFICATIONS ---
SENDER_EMAIL={email}
SENDER_PASSWORD={email_pass}
ADMIN_EMAIL={admin_email}

# --- CONFIGURATION INFRA ---
PORT=10000
DATABASE_URL=gen_pure_omega.db
"""

    with open(".env", "w") as f:
        f.write(env_content)
    
    print("\n[OK] Fichier .env généré. Le périmètre est sécurisé.")
    print("[!] N'oubliez pas d'ajouter '.env' à votre fichier .gitignore !")

if __name__ == "__main__":
    initialize_omega_security()