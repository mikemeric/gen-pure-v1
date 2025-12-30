import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv() # Chargement des munitions depuis le .env

class SpectreAgent:
    """Agent SPECTRE : Unité de Réponse Instantanée par Email"""
    
    def __init__(self):
        self.sender_email = os.getenv("SENDER_EMAIL")
        self.password = os.getenv("SENDER_PASSWORD")
        self.admin_email = os.getenv("ADMIN_EMAIL")

    def send_critical_alert(self, diagnostic):
        """Transmission cryptée de l'alerte à l'État-Major"""
        if not all([self.sender_email, self.password, self.admin_email]):
            print("[!] SPECTRE : Configuration manquante dans le fichier .env")
            return False

        msg = MIMEMultipart()
        msg['From'] = f"GEN-PURE OMEGA <{self.sender_email}>"
        msg['To'] = self.admin_email
        msg['Subject'] = f"🚨 ALERTE CRITIQUE : {diagnostic.get('station')}"

        body = f"""
        ALERTE DE CONTAMINATION DÉTECTÉE
        ---------------------------------
        Station : {diagnostic.get('station')}
        ID Rapport : {diagnostic.get('report_id')}
        Diagnostic : {diagnostic.get('diagnostic')}
        
        Consultez le Dashboard immédiatement pour les mesures d'isolement.
        """
        
        msg.attach(MIMEText(body, 'plain'))

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.sender_email, self.password)
                server.sendmail(self.sender_email, self.admin_email, msg.as_string())
            return True
        except Exception as e:
            print(f"[!] ÉCHEC SPECTRE : {e}")
            return False