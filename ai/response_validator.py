"""
ai/response_validator.py — SUPREME v2.4 (SOVEREIGN GUARD & COMPLETION FIX)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Validador de segurança e qualidade otimizado para evitar cortes de texto.

🔥 UPGRADES DE ELITE (v2.4):
  1. EXPANSÃO DE LIMITE (Fix image_da1d7f): Aumento do limite de 350 para 
     500 caracteres, permitindo que a Cigana seja mais eloquente sem ser podada.
  2. SENTENCE INTEGRITY: Instrução reforçada para NUNCA cortar palavras ou 
     deixar frases pendentes durante a correção de tom ou tamanho.
  3. BALAO LOGIC: Preferência por quebrar em blocos [BALAO] em vez de resumir 
     agressivamente, preservando o misticismo original.
  4. SDK 2.0 READY: Mantém a compatibilidade total com a nova google.genai.
"""

import json
import logging
import os
import re
from typing import Union, List, Dict, Any
from google import genai
from config_cliente import CONFIG_CLIENTE
from schema import Acao

logger = logging.getLogger(__name__)

# Persona fixa e Leis de Validação
SYSTEM_PROMPT = """Você é o Guardião da Qualidade da Cigana Esmeralda.
Sua missão é garantir que a resposta seja mística, segura e perfeitamente formatada para o WhatsApp.

REGRAS DE OURO PARA CORREÇÃO:
1. TOM E ALMA: Calor humano, quiromancia (linhas da mão), sem tom de chatbot ("Claro!", "Com certeza!").
2. BALÕES WHATSAPP: No máximo 4 linhas por bloco; use [BALAO] entre blocos. Limite ~500 caracteres por bloco quando possível.
3. ⚠️ PROIBIÇÃO DE CORTES (CRÍTICO): Cada balão termina com pontuação (. ? …). Nunca palavra cortada.
4. ANTI-IA: Travessões (— –) viram reticências (...).
5. EMOJIS: No máximo 1 por balão, só no final; permitidos: 💜 🔮 🙏 🖐️ ✋ 💔 🕯️ ✨ 😔
6. PROIBIDO: "energia negativa que te acompanha", "Lei da Troca Energética", "isso faz sentido para você?", "me deu um arrepio", "resultado em 5 a 7 dias".

REGRAS DE REJEIÇÃO (aprovada: false):
- Valores financeiros errados (Diferentes de R$ 65 ou R$ 30).
- Promessas de cura médica ou morte.
- Links não autorizados.

Retorne ESTRITAMENTE um JSON:
{
  "aprovada": true,
  "problemas": ["lista"],
  "resposta_corrigida": "texto final completo e pontuado",
  "tipo_resposta": "text"
}
"""

class ResponseValidator:
    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name or CONFIG_CLIENTE.get("modelo_ia", "gemini-2.5-flash")
        self.client = self._inicializar_gemini()

    def _inicializar_gemini(self) -> genai.Client | None:
        if not self.api_key:
            logger.error("🚨 ERRO: GEMINI_API_KEY ausente.")
            return None
        try:
            client = genai.Client(api_key=self.api_key)
            logger.info(f"🛡️ Validador Sovereign Ativo: {self.model_name}")
            return client
        except Exception as e:
            logger.error(f"🚨 Erro ao inicializar ResponseValidator: {e}")
            return None

    @staticmethod
    def _limpar_saida_ia(texto: str) -> str:
        if not texto: return ""
        texto = re.sub(r'`{3}(?:json)?|`{3}', '', texto)
        match = re.search(r'(\{.*\})', texto, re.DOTALL)
        return match.group(1).strip() if match else texto.strip()

    @staticmethod
    def _quebrar_em_baloes(texto: str) -> List[str]:
        return [p.strip() for p in texto.split("[BALAO]") if p.strip()]

    def validar(self, resposta: Union[str, List[Acao]], ctx) -> Union[str, List[Acao]]:
        """Valida e garante a integridade da mensagem final."""
        if not self.client:
            return resposta

        try:
            # Extração de texto para validação
            if isinstance(resposta, list):
                textos = [item.conteudo for item in resposta if isinstance(item, Acao) and item.tipo == "text"]
                if not textos: return resposta
                texto_para_validar = " [BALAO] ".join(textos)
            else:
                texto_para_validar = str(resposta)

            if not texto_para_validar.strip():
                return "🔮 Sinto uma névoa na visão… pode repetir?"

            # Contexto simplificado para o validador
            node_atual = getattr(ctx, "node_atual", "Desconhecido")
            texto_recebido = getattr(ctx, "texto_recebido", "")[:100]
            
            prompt_completo = (
                f"DIRETRIZ:\n{SYSTEM_PROMPT}\n\n"
                f"Contexto: Node {node_atual} | Msg Lead: {texto_recebido}\n\n"
                f"Resposta a validar:\n{texto_para_validar}"
            )

            # Validação com temperatura baixa para precisão
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt_completo,
                config={"temperature": 0.1, "response_mime_type": "application/json"}
            )
            
            data = json.loads(self._limpar_saida_ia(response.text))
            aprovada = data.get("aprovada", True)
            resposta_corrigida = data.get("resposta_corrigida", texto_para_validar)

            if not aprovada:
                logger.warning("🚫 [VALIDATOR] Resposta insegura rejeitada.")
                return "🙏 A visão das suas linhas está confusa agora... me dê um instante."

            # Se a resposta foi corrigida (ex: pontuação adicionada ou quebra de balão)
            if resposta_corrigida != texto_para_validar:
                logger.info("✏️ [VALIDATOR] Resposta ajustada para integridade total.")
                return [Acao(tipo="text", conteudo=balao) for balao in self._quebrar_em_baloes(resposta_corrigida)]
            
            return resposta

        except Exception as e:
            logger.error(f"🚨 [VALIDATOR] Erro inesperado: {e}")
            return resposta