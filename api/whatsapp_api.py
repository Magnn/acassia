import os
import requests
from dotenv import load_dotenv

load_dotenv()

class WhatsAppAPI:
    def __init__(self):
        self.token = os.getenv("WEBAPP_TOKEN")
        self.phone_id = os.getenv("PHONE_NUMBER_ID")
        self.version = "v21.0"
        self.base_url = f"https://graph.facebook.com/{self.version}/{self.phone_id}/messages"
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }

    def enviar_mensagem(self, numero: str, conteudo: str, formato: str = "texto"):
        if not conteudo or str(conteudo).strip() == "":
            return False

        payload = {"messaging_product": "whatsapp", "to": numero}

        if formato == "texto":
            payload["type"] = "text"
            payload["text"] = {"body": conteudo}
        elif formato == "audio":
            payload["type"] = "audio"
            payload["audio"] = {"link": conteudo}
        elif formato == "imagem":
            payload["type"] = "image"
            payload["image"] = {"link": conteudo}

        try:
            response = requests.post(self.base_url, json=payload, headers=self.headers)
            if response.status_code == 200:
                print(f"✅ [API] {formato.upper()} enviado")
                return True
            else:
                print(f"❌ [API ERROR] {response.json()}")
                return False
        except Exception as e:
            print(f"❌ [API ERROR] {e}")
            return False

whatsapp_client = WhatsAppAPI()