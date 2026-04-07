"""
ai/intent_classifier.py — SUPREME v3.0 (Migração SDK google.genai)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Classifica cada mensagem do usuário com base no histórico e no nó atual.

FIX: Migração total para a nova biblioteca 'google.genai' (substituindo a descontinuada google.generativeai).
FIX: Implementação do novo padrão Client para evitar erros de importação.
"""

import json
import logging
import os
import re
from typing import List, Dict, Any, Optional
from google import genai  # ✨ Nova SDK oficial do Google
from config_cliente import CONFIG_CLIENTE

logger = logging.getLogger(__name__)

# Sinais explícitos de intenção comercial (para corrigir falso "preco" no primeiro contato)
_RE_SINAL_PRECO_EXPL = re.compile(
    r"\b(quanto|pre[cç]o|preco|valor|pix|pagar|r\$|reais|parcela|link\s+de\s+pagamento|checkout)\b",
    re.I,
)

# Todas as intenções possíveis no funil
INTENCOES = {
    "compra": "Usuário quer comprar",
    "como_comprar": "Usuário quer saber como adquirir o produto",
    "preco": "Usuário perguntou sobre o valor",
    "duvida_produto": "Usuário tem dúvida sobre o produto",
    "objecao": "Usuário expressou resistência",
    "curiosidade": "Usuário está explorando",
    "engajado": "Usuário responde com entusiasmo",
    "hesitante": "Usuário está indeciso",
    "opt_out": "Usuário quer sair",
    "fora_de_contexto": "Mensagem não relacionada",
    "saudacao": "Usuário está cumprimentando",
    "confirmacao": "Usuário confirmando algo",
    "indefinida": "Não foi possível classificar",
}

# Exemplos para ajudar o Gemini
EXAMPLES = [
    {"texto": "Quanto custa?", "intencao": "preco"},
    {"texto": "Bom dia, me chamo João", "intencao": "saudacao"},
    {"texto": "Boa tarde cigana esmeralda, me chamo Ju", "intencao": "saudacao"},
    {"texto": "Oi Cigana, tudo bem?", "intencao": "saudacao"},
    {"texto": "Quero comprar", "intencao": "compra"},
    {"texto": "Não quero mais mensagens", "intencao": "opt_out"},
]

SYSTEM_PROMPT = """Você é o classificador de intenções da Cigana Esmeralda. 
Sua missão é analisar a mensagem do usuário com base no histórico e no estágio atual do funil.

Categorias:
{categorias}

Exemplos:
{exemplos}

REGRAS DE OURO:
1. Retorne ESTRITAMENTE um JSON válido.
2. NUNCA use o símbolo '—' em qualquer parte da resposta.
3. Se o nome do usuário for Magno, a análise interna deve considerar adjetivos masculinos.
4. Se o usuário confirmar o xeque-mate da leitura, use 'engajado' ou 'confirmacao'.
5. Se o nó atual for de apresentação (1_apresentacao) e a mensagem for só saudação, nome ou cumprimento SEM pedido de valor, use 'saudacao' — não use 'preco' só porque citou "Cigana" ou o nome do bot.
6. "Me chamo", "meu nome é", "boa tarde cigana" com apresentação = sempre 'saudacao', salvo se perguntar quanto custa, valor, preço ou pix na mesma frase.

Formato de saída:
{{"intencao": "nome_da_categoria", "confianca": 0.0, "justificativa": "1 frase curta sem travessões"}}
"""

class IntentClassifier:
    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        # Recomendado usar a versão estável do Gemini Pro para classificação lógica
        self.model_name = model_name or CONFIG_CLIENTE.get("modelo_ia", "gemini-1.5-pro")
        self.client = self._inicializar_cliente()
        self._cache: Dict[str, str] = {}

    def _inicializar_cliente(self) -> genai.Client | None:
        """Inicializa o cliente da nova SDK google.genai."""
        if not self.api_key:
            logger.error("🚨 ERRO: GEMINI_API_KEY ausente.")
            return None
        try:
            # O novo padrão utiliza a classe Client
            client = genai.Client(api_key=self.api_key)
            logger.info(f"🎯 Intent Classifier (SDK 2.0) Conectado: {self.model_name}")
            return client
        except Exception as e:
            logger.error(f"🚨 Erro ao inicializar o Client da Google: {e}")
            return None

    def _ajustar_intencao_primeiro_contato(
        self, texto: str, node_atual: str, intencao: str
    ) -> str:
        """Evita 'preco' quando o lead só se apresenta ou cumprimenta no nó 1."""
        n = (node_atual or "").strip().lower()
        if not n.startswith("1_"):
            return intencao
        t = (texto or "").lower()
        # Regra dura: apresentação + saudação sem palavra de preço = nunca preco
        if intencao == "preco" and not _RE_SINAL_PRECO_EXPL.search(texto or ""):
            if re.search(
                r"\b(me chamo|meu nome|chamo[- ]me|bom dia|boa tarde|boa noite|oi\b|olá|ola)\b",
                t,
            ):
                logger.info(
                    "🎯 [INTENT] ajuste: preco -> saudacao (saudação/apresentação sem sinal comercial)"
                )
                return "saudacao"
        if intencao != "preco":
            return intencao
        if _RE_SINAL_PRECO_EXPL.search(texto or ""):
            return intencao
        sinais = (
            "me chamo",
            "meu nome",
            "sou o ",
            "sou a ",
            "bom dia",
            "boa tarde",
            "boa noite",
            "olá",
            "ola",
            "oi ",
            "oi,",
            "tudo bem",
            "cigana",
        )
        if any(s in t for s in sinais):
            logger.info(
                "🎯 [INTENT] ajuste: preco -> saudacao (primeiro contato sem pedido comercial explícito)"
            )
            return "saudacao"
        return intencao

    def _limpar_json(self, texto: str) -> str:
        """Remove blocos de markdown e limpa a resposta para parsing JSON."""
        if not texto: return ""
        # Remove ```json ... ``` ou ``` ... ```
        texto = re.sub(r'`{3}(?:json)?|`{3}', '', texto)
        # Tenta capturar apenas o conteúdo entre as primeiras e últimas chaves
        match = re.search(r'(\{.*\})', texto, re.DOTALL)
        return match.group(1).strip() if match else texto.strip()

    def _heuristica_saudacao_no1(self, texto: str, node_atual: str) -> Optional[str]:
        """
        Sem chamar o Gemini: saudação + apresentação sem pedido comercial = saudacao.
        Evita falso 'preco' (ex.: 'esmeralda' contendo substrings, cache legado).
        """
        n = (node_atual or "").strip().lower()
        if not n.startswith("1_") or not (texto or "").strip():
            return None
        if _RE_SINAL_PRECO_EXPL.search(texto):
            return None
        tl = texto.lower()
        if re.search(r"me\s+chamo|chamo[- ]?me|meu\s+nome", tl) and any(
            x in tl for x in ("cigana", "bom dia", "boa tarde", "boa noite", "olá", "ola", "oi")
        ):
            return "saudacao"
        if re.match(
            r"^\s*(bom dia|boa tarde|boa noite|oi|olá|ola)\b",
            tl,
        ) and "cigana" in tl:
            return "saudacao"
        return None

    @staticmethod
    def _heuristica_apresentacao_curta_sem_preco(texto: str) -> Optional[str]:
        """
        Saudação + 'me chamo' + menção à cigana/cumprimento, sem pedido de valor.
        Não depende do nó (lead pode estar em 2_/3_ após sniffers ou estado salvo).
        """
        if not (texto or "").strip():
            return None
        if _RE_SINAL_PRECO_EXPL.search(texto):
            return None
        tl = texto.lower()
        if len(tl) > 400:
            return None
        tem_apresentacao = bool(
            re.search(r"\b(me\s+chamo|chamo[- ]?me|meu\s+nome\s+[éeh])\b", tl)
        )
        tem_saudacao = any(
            x in tl
            for x in (
                "cigana",
                "bom dia",
                "boa tarde",
                "boa noite",
                "olá",
                "ola",
                "oi ",
                "oi,",
            )
        )
        if tem_apresentacao and tem_saudacao:
            return "saudacao"
        return None

    def classificar(
        self,
        texto: str,
        historico: List[Any],
        node_atual: str,
        lead_id: Optional[int] = None,
    ) -> str:
        """Classifica a intenção usando o novo método do Client."""
        if not self.client or not texto:
            return "indefinida"

        lid = lead_id if lead_id is not None else "_"
        cache_key = f"{lid}|{node_atual}|{texto[:100]}"

        early = self._heuristica_saudacao_no1(texto, node_atual)
        if not early:
            early = self._heuristica_apresentacao_curta_sem_preco(texto)
        if early:
            self._cache[cache_key] = early
            logger.info(
                "🎯 [INTENT] '%s' → %s (conf=1.00) [heurística]",
                (texto[:48] + "…") if len(texto) > 48 else texto,
                early,
            )
            return early

        if cache_key in self._cache:
            # Sempre reaplica ajuste de primeiro contato (cache pode ter sido gravado antes do fix).
            return self._ajustar_intencao_primeiro_contato(
                texto, node_atual, self._cache[cache_key]
            )

        categorias_fmt = "\n".join(f'- "{k}": {v}' for k, v in INTENCOES.items())
        exemplos_fmt = "\n".join(f'- "{e["texto"]}": {e["intencao"]}' for e in EXAMPLES)
        historico_fmt = self._formatar_historico(historico[-4:])

        prompt_completo = SYSTEM_PROMPT.format(
            categorias=categorias_fmt, exemplos=exemplos_fmt
        ) + f"\n\nNó Atual: {node_atual}\nHistórico:\n{historico_fmt}\nMensagem:\n\"{texto}\"\nClassifique:"

        try:
            # Configuração de geração para a nova SDK
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt_completo,
                config={
                    'temperature': 0.1,
                    'response_mime_type': 'application/json'
                }
            )
            
            raw_text = self._limpar_json(response.text)
            data = json.loads(raw_text)
            
            intencao = str(data.get("intencao", "indefinida")).strip().lower()
            intencao = intencao.replace("preço", "preco").replace("-", "_")
            if intencao not in INTENCOES:
                intencao = "indefinida"
            confianca = float(data.get("confianca", 0.0))
            intencao = self._ajustar_intencao_primeiro_contato(texto, node_atual, intencao)

            logger.info(
                "🎯 [INTENT] '%s' → %s (conf=%.2f)",
                (texto[:48] + "…") if len(texto) > 48 else texto,
                intencao,
                confianca,
            )

            if confianca > 0.8:
                self._cache[cache_key] = intencao

            return intencao

        except Exception as e:
            logger.error(f"🚨 [INTENT] Erro na nova SDK: {e}. Usando fallback.")
            return self._fallback(texto)

    def _formatar_historico(self, historico: List[Any]) -> str:
        linhas = []
        for msg in historico:
            rem = msg.get("remetente", "user") if isinstance(msg, dict) else getattr(msg, "remetente", "user")
            txt = msg.get("texto", "") if isinstance(msg, dict) else getattr(msg, "texto", "")
            prefixo = "👤" if rem == "user" else "🤖"
            linhas.append(f"{prefixo}: {str(txt)[:100]}")
        return "\n".join(linhas)

    def _fallback(self, texto: str) -> str:
        t = texto.lower()
        if any(x in t for x in ["preço", "valor", "quanto"]): return "preco"
        if any(x in t for x in ["comprar", "pagar", "pix"]): return "compra"
        if any(x in t for x in ["parar", "sair", "chega"]): return "opt_out"
        return "indefinida"