import logging
import os

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_TIMEOUT_CONNECT = 5   # segundos para estabelecer conexão
_TIMEOUT_READ    = 15  # segundos para receber a resposta completa


class WhatsAppAPI:
    def __init__(self):
        self.token    = os.getenv("WEBAPP_TOKEN")
        self.phone_id = os.getenv("PHONE_NUMBER_ID")
        self.version  = "v21.0"
        self.base_url = (
            f"https://graph.facebook.com/{self.version}/{self.phone_id}/messages"
        )
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }

    def enviar_mensagem(self, numero: str, conteudo: str, formato: str = "texto") -> bool:
        if not conteudo or str(conteudo).strip() == "":
            return False

        payload: dict = {"messaging_product": "whatsapp", "to": numero}

        if formato == "texto":
            payload["type"] = "text"
            payload["text"] = {"body": conteudo}
        elif formato == "audio":
            payload["type"] = "audio"
            payload["audio"] = {"link": conteudo}
        elif formato == "imagem":
            payload["type"] = "image"
            payload["image"] = {"link": conteudo}
        else:
            logger.warning("[WhatsAppAPI] formato desconhecido: %s", formato)
            return False

        try:
            response = requests.post(
                self.base_url,
                json=payload,
                headers=self.headers,
                timeout=(_TIMEOUT_CONNECT, _TIMEOUT_READ),
            )
            if response.status_code == 200:
                logger.info("[WhatsAppAPI] %s enviado para %s", formato.upper(), numero)
                return True
            logger.error(
                "[WhatsAppAPI] HTTP %s para %s — body: %s",
                response.status_code,
                numero,
                (response.text or "")[:300],
            )
            return False
        except requests.exceptions.Timeout:
            logger.error(
                "[WhatsAppAPI] Timeout ao enviar %s para %s (connect=%ss read=%ss)",
                formato, numero, _TIMEOUT_CONNECT, _TIMEOUT_READ,
            )
            return False
        except requests.exceptions.ConnectionError as exc:
            logger.error("[WhatsAppAPI] Erro de conexão ao enviar para %s: %s", numero, exc)
            return False
        except requests.exceptions.RequestException as exc:
            logger.error("[WhatsAppAPI] Erro inesperado ao enviar para %s: %s", numero, exc)
            return False


whatsapp_client = WhatsAppAPI()
