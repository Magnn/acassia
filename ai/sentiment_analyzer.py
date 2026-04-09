"""
ai/sentiment_analyzer.py — SUPREME v2.3 (Análise Emocional Preditiva)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Módulo de Inteligência Emocional e Detecção de Objeções.

FIX: Migração total para a nova SDK 'google.genai' (Resolução de ImportError).
FIX: Remoção definitiva de 'google.ai'.
FIX: Implementação da previsão de sentimento futuro.
"""

import json
import logging
import os
import re
import time
from typing import List, Dict, Any
from google import genai  # ✨ Nova SDK oficial
from config_cliente import CONFIG_CLIENTE

logger = logging.getLogger(__name__)

# Categorias oficiais para o banco de dados e lógica de recuperação
SENTIMENTOS_VALIDOS = {
    "curioso", "interessado", "hesitante", "comprador",
    "resistente", "animado", "confuso", "frustrado", "padrao",
}

# Prompt mestre focado em vendas e nicho espiritual
SYSTEM_PROMPT = """Analise o sentimento e as objeções na mensagem do WhatsApp.
Você é a inteligência emocional da Cigana Esmeralda.

Retorne um JSON estrito:
{
  "sentimento": "categoria", 
  "score": 0.5, 
  "sinais": [], 
  "objecoes_detectadas": "", 
  "recomendacao_tom": ""
}

REGRAS DE OURO:
1. NUNCA use o símbolo '—' (travessão) nas respostas. Use '...' ou ','.
2. Se o lead for o Magno, use adjetivos masculinos.

Categorias: curioso | interessado | hesitante | comprador | resistente | animado | confuso | frustrado | padrao

Regras de Score (0.0 a 1.0):
- Msg longa com experiência pessoal = +0.3
- Pergunta sobre preço/compra = +0.4
- Monossilábico = -0.2
- Objeção explícita = -0.15
- Compartilha dor real = +0.25
- "não sei/talvez/vou pensar" = -0.2
"""

class SentimentAnalyzer:
    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        """Inicializa o analisador com o novo padrão Client da Google."""
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name or CONFIG_CLIENTE.get("modelo_ia", "gemini-1.5-pro")

        try:
            if self.api_key:
                # ✨ Novo padrão de inicialização SDK 2.0
                self.client = genai.Client(api_key=self.api_key)
                logger.info(f"🧠 Analisador Ativo: {self.model_name}")
            else:
                self.client = None
                logger.error("🚨 ERRO: GEMINI_API_KEY ausente no SentimentAnalyzer.")
        except Exception as e:
            logger.error(f"🚨 Erro na inicialização da API Gemini: {e}")
            self.client = None
        self._quota_cooldown_until = 0.0

    @staticmethod
    def _erro_e_quota_excedida(exc: Exception) -> bool:
        t = str(exc or "").lower()
        return ("resource_exhausted" in t) or ("quota" in t) or ("429" in t)

    def _ativar_cooldown_quota(self, segundos: int = 75) -> None:
        self._quota_cooldown_until = max(self._quota_cooldown_until, time.time() + max(15, segundos))

    def em_cooldown_quota(self) -> bool:
        return time.time() < float(self._quota_cooldown_until or 0.0)

    @staticmethod
    def _limpar_json_sujo(texto: str) -> str:
        """Limpa marcações de markdown e garante JSON puro."""
        if not texto: return ""
        texto = re.sub(r'`{3}(?:json)?|`{3}', '', texto)
        match = re.search(r'(\{.*\})', texto, re.DOTALL)
        return match.group(1).strip() if match else texto.strip()

    def analisar(self, texto: str, historico: list) -> dict:
        """Executa a análise profunda da mensagem do lead."""
        if not self.client or not texto:
            return self._retorno_padrao()
        if self.em_cooldown_quota():
            return self._retorno_padrao()

        # ── Formatação do Histórico (Blindagem contra Dicionários/Objetos) ──
        hist_linhas = []
        for m in historico[-3:]:
            rem = m.get("remetente", "user") if isinstance(m, dict) else getattr(m, "remetente", "user")
            txt = m.get("texto", str(m)) if isinstance(m, dict) else getattr(m, "texto", str(m))
            icone = "👤" if rem == "user" else "🤖"
            hist_linhas.append(f"{icone}: {str(txt)[:100]}")

        hist_fmt = "\n".join(hist_linhas) if hist_linhas else "(início de conversa)"

        prompt_completo = (
            f"DIRETRIZ DE SISTEMA:\n{SYSTEM_PROMPT}\n\n"
            f"HISTÓRICO:\n{hist_fmt}\n\n"
            f"MENSAGEM DO USUÁRIO:\n\"{texto}\""
        )

        try:
            # Configuração via dicionário na nova SDK
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt_completo,
                config={
                    'temperature': 0.1,
                    'response_mime_type': 'application/json'
                }
            )

            raw = self._limpar_json_sujo(response.text)
            data = json.loads(raw)

            sentimento = data.get("sentimento", "padrao").lower()
            if sentimento not in SENTIMENTOS_VALIDOS:
                sentimento = "padrao"

            resultado = {
                "sentimento": sentimento,
                "score": max(0.0, min(1.0, float(data.get("score", 0.5)))),
                "sinais": data.get("sinais", []),
                "objecoes_detectadas": str(data.get("objecoes_detectadas", "")).replace("—", "..."),
                "recomendacao_tom": str(data.get("recomendacao_tom", "")).replace("—", "..."),
            }

            logger.info(f"💭 [SENTIMENT] {sentimento.upper()} | Score: {resultado['score']:.2f}")
            return resultado

        except Exception as e:
            if self._erro_e_quota_excedida(e):
                self._ativar_cooldown_quota(75)
            logger.error(f"🚨 [SENTIMENT] Falha na chamada Gemini: {e}")
            return self._retorno_padrao()

    def prever_proximo_sentimento(self, historico: list) -> str:
        """Prevê o próximo sentimento do lead com base no histórico."""
        if not self.client or not historico:
            return "padrao"

        hist_fmt = "\n".join([str(m)[:100] for m in historico[-5:]])
        prompt_prever = (
            f"Com base no histórico abaixo, qual será o provável sentimento do usuário na próxima mensagem?\n\n"
            f"{hist_fmt}\n\n"
            f"Categorias: {', '.join(SENTIMENTOS_VALIDOS)}\n"
            "Responda APENAS com a categoria em letras minúsculas."
        )

        try:
            if self.em_cooldown_quota():
                return "padrao"
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt_prever,
                config={'temperature': 0.3}
            )
            sentimento = response.text.strip().lower()
            return sentimento if sentimento in SENTIMENTOS_VALIDOS else "padrao"
        except Exception as e:
            if self._erro_e_quota_excedida(e):
                self._ativar_cooldown_quota(75)
            logger.error(f"🚨 [PREDICT] Falha na previsão: {e}")
            return "padrao"

    def _retorno_padrao(self) -> dict:
        return {
            "sentimento": "padrao",
            "score": 0.5,
            "sinais": [],
            "objecoes_detectadas": "",
            "recomendacao_tom": "Mantenha o tom místico e acolhedor.",
        }