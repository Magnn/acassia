"""
personalizer.py — Versão SUPREME v2.3 (Otimização e Segurança)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MEMÓRIA COMPLETA: Histórico + Metadados (Fatos do Lead)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔥 Melhorias de segurança e tratamento de erros.
"""

import logging
import os
import re
import requests
import json
from PIL import Image
from io import BytesIO
from google import genai
from google.genai import errors as genai_errors
from config_cliente import CONFIG_CLIENTE
from typing import Any, Dict, List, Optional, Tuple, Union
from copy_sanitizer import (
    nome_lead_para_exibicao,
    preparar_texto_envio,
    resumo_dor_para_copy,
)

logger = logging.getLogger(__name__)

class Personalizer:
    def __init__(self, api_key: str | None = None, model_name: str | None = None):
        self.api_key = os.getenv("GEMINI_API_KEY") or api_key
        self.model_name = model_name or CONFIG_CLIENTE.get("modelo_ia", "gemini-2.5-flash")
        self.client = self._inicializar_gemini()

    def _inicializar_gemini(self):
        """Inicializa o cliente Gemini e trata possíveis erros."""
        if not self.api_key:
            logger.error("🚨 ERRO: GEMINI_API_KEY ausente.")
            return None
        try:
            client = genai.Client(api_key=self.api_key)
            logger.info(f"🔮 Oráculo Conectado: {self.model_name} [Memória Completa Ativa]")
            return client
        except Exception as e:
            logger.error(f"🚨 Erro na inicialização do Personalizer: {e}")
            return None

    @staticmethod
    def _limpar_json(texto: str) -> str:
        """
        Extrai JSON válido da resposta do modelo (markdown ```json, texto extra, etc.).
        Usa json.JSONDecoder.raw_decode quando possível para não depender de regex gulosa.
        """
        if not texto:
            return "{}"
        t = re.sub(r"```(?:json)?\s*|```", "", texto, flags=re.I).strip()
        start = t.find("{")
        if start == -1:
            return t
        chunk = t[start:]
        decoder = json.JSONDecoder()
        try:
            _, end = decoder.raw_decode(chunk)
            return chunk[:end].strip()
        except json.JSONDecodeError:
            pass
        m = re.search(r"\{[\s\S]*\}", chunk)
        return m.group(0).strip() if m else chunk.strip()

    _NODE1_CHAVES_ORDEM: Tuple[str, ...] = (
        "extra",
        "A_saudacao",
        "B_apresentacao",
        "C_nome",
        "D_confirmacao",
    )

    @classmethod
    def _extrair_node1_json_malformado(cls, texto: str) -> Dict[str, Any]:
        """
        Último recurso quando o modelo devolve JSON inválido (aspas não escapadas,
        string truncada, etc.): lê cada campo na ordem do schema.
        """
        out: dict[str, Any] = {}
        if not texto:
            return out
        t = re.sub(r"```(?:json)?\s*|```", "", texto, flags=re.I).strip()
        for key in cls._NODE1_CHAVES_ORDEM:
            needle = f'"{key}"'
            pos = t.find(needle)
            if pos == -1:
                continue
            j = pos + len(needle)
            while j < len(t) and t[j] in " \t\n\r":
                j += 1
            if j >= len(t) or t[j] != ":":
                continue
            j += 1
            while j < len(t) and t[j] in " \t\n\r":
                j += 1
            if j >= len(t):
                continue
            if t[j : j + 4] == "null":
                out[key] = None
                continue
            if t[j] != '"':
                continue
            j += 1
            buf: list[str] = []
            while j < len(t):
                c = t[j]
                if c == "\\" and j + 1 < len(t):
                    esc = t[j : j + 2]
                    buf.append(esc)
                    j += 2
                    continue
                if c == '"':
                    j += 1
                    break
                buf.append(c)
                j += 1
            out[key] = "".join(buf)
        return out

    @classmethod
    def _parsear_node1_dict(cls, raw_resposta: str) -> Dict[str, Any]:
        """Tenta json.loads; se falhar, extrai campos soltos do texto bruto."""
        limpo = cls._limpar_json(raw_resposta)
        try:
            data = json.loads(limpo)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError as e:
            loose = cls._extrair_node1_json_malformado(raw_resposta)
            if not loose:
                loose = cls._extrair_node1_json_malformado(limpo)
            if loose:
                logger.debug(
                    "[NODE1 JSON] parse padrão falhou; extração tolerante ok (%s)",
                    e,
                )
                return loose
            logger.warning(
                "⚠️ [NODE1 JSON] JSON inválido e extração vazia (%s)",
                e,
            )
            return {}

    @staticmethod
    def _limpar_saida_ia(texto: str) -> str:
        """Remove prefixos e marcadores para manter a fluidez natural."""
        if not texto:
            return ""
        limpo = texto.strip()
        marcadores = [
            "RESPOSTA DA CIGANA:", "RESPOSTA DA CIGANA",
            "CIGANA:", "RESPOSTA:", "###", "SISTEMA:",
        ]
        for marcador in marcadores:
            limpo = limpo.replace(marcador, "")
        return limpo.strip()

    @staticmethod
    def _append_instrucao_etapa(metadata: Optional[dict], prompt: str) -> str:
        """Injeta bloco_instrucao de stage_intel (ai.stage_intelligence) quando existir."""
        if not metadata:
            return prompt
        si = metadata.get("stage_intel") or {}
        block = (si.get("bloco_instrucao") or "").strip()
        if not block:
            return prompt
        return (
            f"{prompt}\n\n"
            "ROTEIRO DA ETAPA (integre depois de atender a última mensagem do cliente; não a substitua):\n"
            f"{block}\n"
        )

    @staticmethod
    def _bloco_acassia_studio(metadata: Optional[dict]) -> str:
        """Perfil publicado do Studio AcassIA (engine injeta __acassia_studio__)."""
        if not isinstance(metadata, dict):
            return ""
        snap = metadata.get("__acassia_studio__")
        if not isinstance(snap, dict):
            return ""
        data = snap.get("data")
        if not isinstance(data, dict):
            return ""
        nome = str(snap.get("agent_name") or "").strip()
        vn = snap.get("version_number")
        head = (
            f"PERFIL AGENTE ACASSIA PUBLICADO (v{vn}"
            + (f" — {nome}" if nome else "")
            + "):\n"
        )
        linhas: list[str] = [head]
        p = data.get("personalidade") if isinstance(data.get("personalidade"), dict) else {}
        if p:
            if (p.get("identidade") or "").strip():
                linhas.append(f"- Identidade: {str(p['identidade']).strip()[:1200]}")
            if (p.get("diretrizes") or "").strip():
                linhas.append(f"- Diretrizes de voz: {str(p['diretrizes']).strip()[:1200]}")
            if (p.get("voz") or "").strip():
                linhas.append(f"- Registro de voz: {str(p['voz']).strip()[:120]}")
            for k in ("estabilidade", "similaridade", "sotaque", "velocidade"):
                if p.get(k) is not None:
                    linhas.append(f"- {k}: {p.get(k)}")
        ins = data.get("instrucoes") if isinstance(data.get("instrucoes"), dict) else {}
        if ins:
            if (ins.get("gerais") or "").strip():
                linhas.append(f"- Instruções gerais: {str(ins['gerais']).strip()[:2200]}")
            if (ins.get("proibicoes") or "").strip():
                linhas.append(f"- Proibições: {str(ins['proibicoes']).strip()[:1200]}")
            if (ins.get("formato_saida") or "").strip():
                linhas.append(f"- Formato de saída: {str(ins['formato_saida']).strip()[:800]}")
        base = data.get("base") if isinstance(data.get("base"), dict) else {}
        if base:
            for k, label in (
                ("contexto_empresa", "Contexto empresa"),
                ("produtos", "Produtos/ofertas"),
                ("politica_preco", "Preço e negociação"),
            ):
                if (base.get(k) or "").strip():
                    linhas.append(f"- {label}: {str(base[k]).strip()[:2400]}")
        faq = data.get("faq") if isinstance(data.get("faq"), dict) else {}
        if (faq.get("perguntas") or "").strip():
            linhas.append(f"- FAQ: {str(faq['perguntas']).strip()[:2400]}")
        arq = data.get("arquivos") if isinstance(data.get("arquivos"), dict) else {}
        if (arq.get("links") or "").strip():
            linhas.append(f"- Referências/links: {str(arq['links']).strip()[:1200]}")
        if len(linhas) <= 1:
            return ""
        return "\n".join(linhas) + "\n\n"

    @staticmethod
    def _bloco_copy_guardrails(metadata: Optional[dict]) -> str:
        """Tom e promessas a evitar — vem de config copy_guardrails."""
        cfg = (metadata or {}).get("__config__") if isinstance(metadata, dict) else None
        if not isinstance(cfg, dict):
            return ""
        cg = cfg.get("copy_guardrails") or {}
        evitar = cg.get("tom_evitar") or []
        nao_prom = (cg.get("nao_prometer") or "").strip()
        partes: list[str] = []
        if evitar:
            partes.append(
                "GUARDRAILS DE TOM: não usar pressão barata nem promessas vedadas; evitar expressões como: "
                + ", ".join(str(x) for x in evitar[:12])
                + ("" if len(evitar) <= 12 else "…")
            )
        if nao_prom:
            partes.append(f"NÃO PROMETER (área sensível): {nao_prom}")
        if not partes:
            return ""
        return "\n".join(partes) + "\n\n"

    @staticmethod
    def _bloco_prioridade_ultima_mensagem(metadata: Optional[dict]) -> str:
        """Prioriza Q&A sobre o roteiro; reforço quando várias dúvidas no mesmo turno."""
        if metadata and metadata.get("node_copy_venda_direta"):
            return (
                "PRIORIDADE DESTA ETAPA: **venda direta no WhatsApp** — copy enxuta que sustenta o **produto** "
                "(trabalho nomeado no system) e não perde o fio comercial. "
                "Não expandir em leitura longa nem aula; cada bloco empurra decisão ou confiança na decisão. "
                "Se a última mensagem for tangencial, 1 frase de ponte e volte ao roteiro do nó (agitação ou oferta).\n\n"
            )
        if metadata and metadata.get("node_leitura_profunda"):
            return (
                "PRIORIDADE DESTA ETAPA: leitura LONGA e PROFUNDA em vários blocos (BLOCO_1:: … BLOCO_N::). "
                "Não resuma em poucas frases: cada bloco deve ter densidade para o lead se identificar. "
                "Depois integre o roteiro da etapa sem ignorar o que a última mensagem pediu.\n\n"
            )
        si = (metadata or {}).get("stage_intel") or {}
        if si.get("varias_perguntas_detectadas"):
            return (
                "PRIORIDADE ABSOLUTA: A última mensagem do cliente parece trazer VÁRIAS dúvidas ou tópicos. "
                "Responda a CADA um com clareza (linhas curtas ou um parágrafo por tema). "
                "Só depois alinhe ao roteiro da etapa abaixo, sem pular pontos nem soar evasivo.\n\n"
            )
        return (
            "PRIORIDADE: Responda primeiro ao que a última mensagem do cliente pediu, perguntou ou revelou. "
            "Depois integre o roteiro da etapa sem ignorar o que já foi endereçado.\n\n"
        )

    def _montar_fatos_contexto(self, metadata: dict) -> str:
        """Extrai dados do metadata e transforma em fatos para a IA."""
        if not metadata:
            return "Nenhum fato conhecido ainda."

        fatos = []
        cfg = metadata.get("__config__") if isinstance(metadata, dict) else None
        if isinstance(cfg, dict):
            pn = cfg.get("perfil_negocio") or {}
            if isinstance(pn, dict):
                if pn.get("promessa_principal"):
                    fatos.append(f"- Promessa do negócio (não violar): {pn['promessa_principal']}")
                if pn.get("para_quem_nao_e"):
                    fatos.append(f"- Não posicionar para: {pn['para_quem_nao_e']}")
                if pn.get("prova_curta"):
                    fatos.append(f"- Prova social (hint): {pn['prova_curta']}")
        if metadata.get("nome_lead"):
            _nm = nome_lead_para_exibicao(str(metadata["nome_lead"]))
            fatos.append(f"- Nome (vocativo curto; não repetir frases longas do cliente): {_nm}")
        if metadata.get("universo_desejo"):
            fatos.append(f"- Universo: {metadata['universo_desejo']}")
        if metadata.get("resumo_dor"):
            _dor_f = resumo_dor_para_copy(str(metadata["resumo_dor"]), max_len=100)
            fatos.append(f"- Dor Central (resumo curto, não cite texto de abertura nem preço): {_dor_f}")
        if metadata.get("desejo_oculto"):
            _dz = re.sub(r"\s+", " ", str(metadata["desejo_oculto"]).strip())[:220]
            if _dz:
                fatos.append(f"- Desejo Profundo (resumo): {_dz}")
        if metadata.get("detalhe_especifico"):
            fatos.append(f"- Detalhes: {metadata['detalhe_especifico']}")

        si = metadata.get("stage_intel") or {}
        if isinstance(si, dict) and si:
            if si.get("prioridade"):
                fatos.append(f"- Foco da etapa: {si['prioridade']}")
            if si.get("varias_perguntas_detectadas"):
                fatos.append(
                    "- Várias perguntas/tópicos no mesmo turno: responder todas antes de só avançar o script."
                )
            if si.get("nome_elegivel_elogio") is False:
                fatos.append("- Nome ainda não é ideal para elogio direto (peça primeiro nome com naturalidade).")
            if si.get("preco_prematuro"):
                fatos.append("- Lead trouxe preço/valor fora da ordem: acolher e ponte para a meta desta etapa.")
            elif si.get("curiosidade_ou_desconfianca"):
                fatos.append("- Sinal de curiosidade ou desconfiança: validar sem defensividade.")

        return "\n".join(fatos) if fatos else "Início de conexão."

    def _formatar_historico(self, historico_lista: list, mensagem_lead: str = "") -> str:
        """Formata o histórico de mensagens para o prompt."""
        linhas = []
        for m in historico_lista[-20:] if historico_lista else []:
            rem = getattr(m, "remetente", None) or (m.get("remetente") if isinstance(m, dict) else "")
            txt = getattr(m, "texto", None) or (m.get("texto") if isinstance(m, dict) else str(m))
            if txt and not txt.startswith("[") and not txt.startswith("SISTEMA_"):
                quem = "Cliente" if rem == "user" else "Cigana"
                linhas.append(f"{quem}: {txt}")
        # Evita duplicar a última mensagem: o engine já a gravou no histórico e repete em ÚLTIMA MENSAGEM.
        dup = (mensagem_lead or "").strip()
        if dup and linhas:
            ult = linhas[-1]
            if ult.startswith("Cliente:"):
                corpo = ult.split("Cliente:", 1)[1].strip()
                if corpo == dup:
                    linhas.pop()
        return "\n".join(linhas)

    @staticmethod
    def _aprox_tokens(texto: str) -> int:
        t = str(texto or "")
        if not t:
            return 0
        return max(1, len(t) // 4)

    @staticmethod
    def _cfg_ia_economia(metadata: Optional[dict]) -> dict:
        cfg = (metadata or {}).get("__config__") if isinstance(metadata, dict) else None
        if not isinstance(cfg, dict):
            return {}
        ie = cfg.get("ia_economia") or {}
        return ie if isinstance(ie, dict) else {}

    def _aplicar_guardrails_custo(
        self,
        *,
        metadata: Optional[dict],
        max_tokens_solicitado: int,
        temperatura_solicitada: float,
    ) -> tuple[int, float]:
        ie = self._cfg_ia_economia(metadata)
        max_default = int(ie.get("max_output_tokens_default", 900) or 900)
        budget = int(ie.get("orcamento_tokens_por_lead", 12000) or 12000)
        ratio = float(ie.get("modo_economico_ratio", 0.8) or 0.8)
        node = str((metadata or {}).get("node_atual_exec") or "")
        por_node = ie.get("max_output_tokens_por_node") or {}
        cap_node = int(por_node.get(node, max_default) or max_default) if isinstance(por_node, dict) else max_default
        max_tokens = min(int(max_tokens_solicitado or max_default), cap_node)
        temp = float(temperatura_solicitada)
        gastos = int((metadata or {}).get("_ia_tokens_gastos_aprox", 0) or 0)
        if gastos >= int(budget * ratio):
            max_tokens = max(280, int(max_tokens * 0.65))
            temp = min(temp, 0.72)
            if isinstance(metadata, dict):
                metadata["_ia_modo_economico"] = True
        return max_tokens, temp

    def _registrar_consumo_ia(self, metadata: Optional[dict], prompt: str, resposta: str) -> None:
        if not isinstance(metadata, dict):
            return
        gastos = int(metadata.get("_ia_tokens_gastos_aprox", 0) or 0)
        gastos += self._aprox_tokens(prompt) + self._aprox_tokens(resposta)
        metadata["_ia_tokens_gastos_aprox"] = gastos

    def gerar_resposta(
        self,
        *,
        system_prompt: str,
        historico_lista: list,
        mensagem_lead: str,
        metadata: dict = None,
        max_output_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
    ) -> str:
        """Gera resposta textual com histórico e metadados."""
        if not self.client:
            return "Oráculo offline."

        try:
            contexto_dialogo = self._formatar_historico(historico_lista, mensagem_lead=mensagem_lead)
            fatos_cliente = self._montar_fatos_contexto(metadata)
            prioridade = self._bloco_prioridade_ultima_mensagem(metadata)
            guard = self._bloco_copy_guardrails(metadata)
            studio = self._bloco_acassia_studio(metadata)
            si = (metadata or {}).get("stage_intel") or {}
            longo = bool(si.get("varias_perguntas_detectadas"))

            prompt_final = (
                f"{prioridade}{guard}{studio}"
                f"DIRETRIZ DE PERSONALIDADE:\n{system_prompt}\n\n"
                f"FATOS CONHECIDOS SOBRE O CLIENTE (Não esqueça disto):\n{fatos_cliente}\n\n"
                f"HISTÓRICO RECENTE DA CONVERSA:\n{contexto_dialogo}\n\n"
                f"ÚLTIMA MENSAGEM DO CLIENTE: {mensagem_lead}\n\n"
                "RESPOSTA DA CIGANA (Mística, acolhedora e direta):"
            )
            prompt_final = self._append_instrucao_etapa(metadata, prompt_final)

            if max_output_tokens is not None:
                max_tokens = max_output_tokens
            else:
                max_tokens = 1200 if longo else 1000
            temp = 0.9 if temperature is None else temperature
            max_tokens, temp = self._aplicar_guardrails_custo(
                metadata=metadata,
                max_tokens_solicitado=max_tokens,
                temperatura_solicitada=temp,
            )
            config = {"max_output_tokens": max_tokens, "temperature": temp}
            resposta = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt_final,
                config=config
            )
            saida = preparar_texto_envio(self._limpar_saida_ia(resposta.text or ""), "personalizer_text")
            self._registrar_consumo_ia(metadata, prompt_final, saida)
            return saida

        except genai_errors.GenerativeModelError as e:
            logger.error(f"❌ Erro na geração de texto: {e}")
            return "As cartas se embaralharam. Sinto uma névoa, tente novamente em instantes."
        except Exception as e:
            logger.error(f"🚨 Erro inesperado: {e}")
            return "🙏 Algo se moveu no astral... me dê mais um instante."

    def gerar_node1_json(
        self,
        *,
        system_prompt: str,
        historico_lista: list,
        mensagem_lead: str,
        metadata: Optional[dict] = None,
    ) -> dict:
        """
        Nó 1: saída JSON com hierarquia fixa (extra opcional + A + B + C? + D).
        Evita truncamento tipo 'Eu sou Esmer' típico de texto livre com [BALAO].
        """
        if not self.client:
            return {}
        try:
            contexto_dialogo = self._formatar_historico(historico_lista, mensagem_lead=mensagem_lead)
            fatos_cliente = self._montar_fatos_contexto(metadata)
            prioridade = self._bloco_prioridade_ultima_mensagem(metadata)
            guard = self._bloco_copy_guardrails(metadata)
            studio = self._bloco_acassia_studio(metadata)
            prompt_final = (
                f"{prioridade}{guard}{studio}"
                f"{system_prompt}\n\n"
                f"FATOS CONHECIDOS SOBRE O CLIENTE:\n{fatos_cliente}\n\n"
                f"HISTÓRICO RECENTE:\n{contexto_dialogo}\n\n"
                f"ÚLTIMA MENSAGEM DO CLIENTE (inclui briefing se houver):\n{mensagem_lead}\n\n"
                "Responda SOMENTE com um objeto JSON válido UTF-8 (sem markdown). "
                "Dentro de cada string use \\\" para aspas e \\\\n para quebra de linha — nunca aspas cruas no meio do texto.\n"
                "Chaves obrigatórias:\n"
                '- "extra": string ou null. Se o briefing pedir acolhimento de dor/preço/amor, preencha com 1–2 frases. '
                "Se não couber nada, null.\n"
                '- "A_saudacao": string. Saudação + boas-vindas ao espaço (instituto de luz chamado Meu Mistério — no máximo aqui neste turno).\n'
                '- "B_apresentacao": string. Quem é a Esmeralda e como acompanha o lead — sem repetir o instituto se já apareceu em A ou extra.\n'
                '- "C_nome": string ou null. Se pedir nome, use tom humano tipo: Me diz como você se chama, meu bem? Assim eu te falo direito.\n'
                '- "D_confirmacao": string ou null. Se C_nome já pergunta o nome e fecha o turno, use null (não mande segundo CTA de sim).\n'
                "Anti-repetição: no máximo um bloco institucional (instituto de luz chamado Meu Mistério) entre extra e A; B sem remarcar a mesma frase. "
                "Vaga gratuita: no máximo uma vez (prefira extra ou D).\n"
            )
            prompt_final = self._append_instrucao_etapa(metadata, prompt_final)
            resposta = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt_final,
                config={
                    "temperature": 0.52,
                    "max_output_tokens": self._aplicar_guardrails_custo(
                        metadata=metadata, max_tokens_solicitado=1400, temperatura_solicitada=0.52
                    )[0],
                    "response_mime_type": "application/json",
                },
            )
            raw = (resposta.text or "").strip()
            self._registrar_consumo_ia(metadata, prompt_final, raw)
            data = self._parsear_node1_dict(raw)
            return data if isinstance(data, dict) else {}
        except Exception as e:
            logger.error(f"🚨 [NODE1 JSON] {e}")
            return {}

    def gerar_resposta_com_imagem(self, system_prompt: str, imagem_url: str, mensagem_lead: str, metadata: dict = None) -> str:
        """Analisa imagem (palma da mão) integrando com a memória completa do lead."""
        if not self.client:
            return ""

        try:
            resp = requests.get(imagem_url, timeout=15)
            if resp.status_code != 200:
                logger.warning(f"⚠️ Imagem não encontrada: Status {resp.status_code}")
                return ""

            img = Image.open(BytesIO(resp.content))
            fatos_cliente = self._montar_fatos_contexto(metadata)
            prioridade = self._bloco_prioridade_ultima_mensagem(metadata)
            guard = self._bloco_copy_guardrails(metadata)
            studio = self._bloco_acassia_studio(metadata)
            si = (metadata or {}).get("stage_intel") or {}
            longo = bool(si.get("varias_perguntas_detectadas"))

            prompt_final = (
                f"{prioridade}{guard}{studio}"
                f"SISTEMA: {system_prompt}\n\n"
                f"FATOS SOBRE O CLIENTE:\n{fatos_cliente}\n\n"
                f"MENSAGEM ANEXA: {mensagem_lead}"
            )
            prompt_final = self._append_instrucao_etapa(metadata, prompt_final)

            config = {"temperature": 0.1, "max_output_tokens": 700 if longo else 500}
            config["max_output_tokens"], config["temperature"] = self._aplicar_guardrails_custo(
                metadata=metadata,
                max_tokens_solicitado=config["max_output_tokens"],
                temperatura_solicitada=config["temperature"],
            )
            resposta = self.client.models.generate_content(
                model=self.model_name,
                contents=[prompt_final, img],
                config=config
            )
            saida = preparar_texto_envio(self._limpar_saida_ia(resposta.text or ""), "personalizer_vision")
            self._registrar_consumo_ia(metadata, prompt_final, saida)
            return saida

        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Erro ao obter imagem: {e}")
            return ""
        except Exception as e:
            logger.error(f"🚨 [VISION] Erro na análise multimodal: {e}")
            return ""