"""
ai/context_compressor.py — SUPREME v2.2 (Eficiência e Robustez com Nova SDK)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Compressor Semântico de Histórico de Conversa.

FIX: Combinação da estrutura simplificada do Magno com a nova SDK 'google.genai'.
FIX: Remoção do import obsoleto 'google.ai' para evitar ImportError.
"""

import logging
import os
from typing import List, Dict, Tuple, Any
from google import genai
from config_cliente import CONFIG_CLIENTE

logger = logging.getLogger(__name__)

# Prompt Simplificado e Focado
SYSTEM_PROMPT = """Resuma a conversa do WhatsApp preservando informações pessoais, objeções, interesse e pendências (máx. 200 palavras)."""


class ContextCompressor:
    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name or CONFIG_CLIENTE.get("modelo_ia", "gemini-2.5-flash")
        self._cache: Dict[Tuple[int, int], str] = {}
        
        try:
            if self.api_key:
                # ✨ Novo padrão da SDK: genai.Client
                self.client = genai.Client(api_key=self.api_key, http_options={"timeout": 90})
                logger.info(f"🗜️ Compressor Conectado: {self.model_name}")
            else:
                self.client = None
                logger.error("⚠️ GEMINI_API_KEY ausente para o ContextCompressor.")
        except Exception as e:
            logger.error(f"🚨 Erro ao inicializar ContextCompressor: {e}")
            self.client = None

    def comprimir(self, historico: List[Any]) -> str:
        """Comprime o histórico em um resumo estruturado."""
        if not historico:
            return ""

        if not self.client:
            return self._resumo_fallback(historico)

        ultimo_msg = historico[-1]
        ultimo_id = getattr(ultimo_msg, "id", None) or (ultimo_msg.get("id") if isinstance(ultimo_msg, dict) else len(historico))
        cache_key = (len(historico), ultimo_id)

        if cache_key in self._cache:
            logger.debug("📋 [COMPRESSOR] Usando cache.")
            return self._cache[cache_key]

        conversa_fmt = self._formatar_conversa(historico)
        prompt_completo = f"Resuma:\n\n{conversa_fmt}\n\n{SYSTEM_PROMPT}"

        import time
        for tentativa in range(3):
            try:
                config = {"temperature": 0.2, "max_output_tokens": 400}
                
                # ✨ Chamada geradora da nova SDK
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt_completo,
                    config=config
                )
                
                resumo = (response.text or "").replace("```markdown", "").replace("```", "").strip()
                self._cache[cache_key] = resumo
                
                logger.info(f"📦 [COMPRESSOR] {len(historico)} msgs → resumo de {len(resumo)} chars")
                return resumo

            except Exception as e:
                err_str = str(e).lower()
                if "timeout" in err_str or "ssl" in err_str or "handshake" in err_str or "503" in err_str:
                    if tentativa < 2:
                        logger.warning(f"⚠️ [COMPRESSOR] Timeout/SSL Gemini (tentativa {tentativa+1}/3). Retentando sem recriar cliente...")
                        time.sleep(1.5)
                        continue
                logger.error(f"🚨 [COMPRESSOR] Erro ao comprimir: {e}")
                return self._resumo_fallback(historico)

        return self._resumo_fallback(historico)

    def _formatar_conversa(self, historico: List[Any]) -> str:
        """Formata o histórico para o prompt."""
        linhas = []
        for msg in historico:
            remetente = msg.get("remetente", "user") if isinstance(msg, dict) else getattr(msg, "remetente", "user")
            texto_msg = msg.get("texto", str(msg)) if isinstance(msg, dict) else getattr(msg, "texto", str(msg))
            ts = msg.get("timestamp", "") if isinstance(msg, dict) else getattr(msg, "timestamp", "")
            ts_str = ts.strftime("%H:%M") if hasattr(ts, "strftime") else str(ts)

            prefixo = f"[{ts_str}] " if ts_str else ""
            nome_remetente = "Usuário" if remetente == "user" else "Bot"
            linhas.append(f"{prefixo}{nome_remetente}: {texto_msg}")

        return "\n".join(linhas)

    def _resumo_fallback(self, historico: List[Any]) -> str:
        """Gera um resumo básico em caso de falha da IA."""
        ultimas = historico[-3:]
        linhas_fallback = []
        for msg in ultimas:
            rem = msg.get("remetente", "user") if isinstance(msg, dict) else getattr(msg, "remetente", "user")
            txt = msg.get("texto", str(msg)) if isinstance(msg, dict) else getattr(msg, "texto", str(msg))
            linhas_fallback.append(f"{'U' if rem == 'user' else 'B'}: {txt[:60]}")

        return "JORNADA: " + " | ".join(linhas_fallback)