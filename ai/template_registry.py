"""
ai/template_registry.py — SUPREME v3.5 (Fix DB Insertion & A/B Testing)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Registry de Templates de Recuperação Validados por IA com A/B Testing.

🔥 UPGRADE (v3.5):
  1. FIX FATAL KWARG: Remoção da linha `variaveis_detectadas` que estava a 
     causar o crash no Motor de Recuperação. Agora o insert é 100% compatível 
     com a tabela `TemplateMsg` do `db/models.py`.
  2. GÊNERO BLINDADO: A IA recebe instruções estritas para o Magno.
"""

import json
import logging
import re
import os
import threading
from datetime import datetime, timezone
from typing import Optional

from google import genai

from db.database import SessionLocal
from db.models import TemplateMsg
from config_cliente import CONFIG_CLIENTE
from flows.funnel_gates import VOCATIVO_SEM_NOME

logger = logging.getLogger(__name__)

USOS_PARA_REFRESH = 50  # Após 50 usos, o sistema avalia se gera um novo copy para teste A/B
MAX_VARIANTES = 2

class TemplateRegistry:
    def __init__(self, api_key: str = None, model_name: str = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        # Lê o modelo dinamicamente das configurações centrais
        self.model_name = model_name or CONFIG_CLIENTE.get("modelo_ia", "gemini-2.5-flash")
        self._cache_memoria: dict[str, str] = {}
        
        try:
            if self.api_key:
                self.client = genai.Client(api_key=self.api_key)
                logger.info("[template_registry] v3.5 ativo model=%s", self.model_name)
            else:
                self.client = None
                logger.error("⚠️ GEMINI_API_KEY ausente para o TemplateRegistry.")
        except Exception as e:
            logger.error(f"🚨 Erro ao inicializar TemplateRegistry: {e}")
            self.client = None

    # ──────────────────────────────────────────
    # INTERFACE PRINCIPAL
    # ──────────────────────────────────────────
    def obter_ou_gerar(
        self,
        categoria: str,         # "recuperacao_1" (5m) | "recuperacao_2" (1h) | "recuperacao_3" (3h)
        node: str,               # node onde o lead silenciou
        contexto_geracao: dict,  # contexto emocional e histórico
        variaveis: dict,         # {"nome": "Magno"}
    ) -> str:
        """Busca o melhor template no DB ou gera um novo via IA."""
        chave_base = f"{categoria}_{self._normalizar_node(node)}"
        template_body = self._buscar_melhor_template(chave_base)

        if template_body is None:
            logger.info("🆕 [REGISTRY] Gerando recuperação estratégica para '%s'...", chave_base)
            template_body = self._gerar_e_salvar(chave_base, categoria, node, contexto_geracao)

        self._registrar_uso(chave_base)
        return self._sanear_corpo_template_final(
            self._substituir_variaveis(template_body, variaveis)
        )

    # ──────────────────────────────────────────
    # BUSCA E GESTÃO DE PERFORMANCE (A/B TESTING)
    # ──────────────────────────────────────────
    def _buscar_melhor_template(self, chave_base: str) -> Optional[str]:
        """Recupera o template com melhor score de conversão."""
        if chave_base in self._cache_memoria:
            return self._cache_memoria[chave_base]

        db = SessionLocal()
        try:
            templates = (
                db.query(TemplateMsg)
                .filter(
                    TemplateMsg.chave_base == chave_base,
                    TemplateMsg.ativo == True,
                )
                .order_by(TemplateMsg.score_conversao.desc())
                .all()
            )
            
            if not templates:
                return None

            melhor = templates[0]

            # Lógica de Refresh: Se o template já foi muito usado, agendamos um teste de nova variante
            if melhor.total_usos >= USOS_PARA_REFRESH:
                self._agendar_refresh(chave_base, melhor)

            self._cache_memoria[chave_base] = melhor.corpo
            return melhor.corpo
        finally:
            db.close()

    # ──────────────────────────────────────────
    # GERAÇÃO VIA IA (O CÉREBRO DA CIGANA)
    # ──────────────────────────────────────────
    def _gerar_e_salvar(self, chave_base: str, categoria: str, node: str, contexto: dict) -> str:
        """Chama o Gemini para criar uma copy contextualizada e masculina."""
        if not self.client:
            return self._fallback_hardcoded(categoria)

        system_instruction = self._system_por_categoria(categoria)
        node_label = self._node_para_label(node)
        
        sentimento = contexto.get("sentimento", "padrao")
        historico = contexto.get("historico_resumido", "Sem histórico.")

        prompt_usuario = f"""Gere UMA mensagem de recuperação para: {node_label}
O lead silenciou nesta etapa. 
Sentimento detectado: {sentimento}
Contexto recente: {historico}

REGRAS OBRIGATÓRIAS:
1. TRATAMENTO DE GÊNERO: Se o nome for MAGNO, use adjetivos masculinos (preparado, focado, sozinho).
2. Use APENAS {{{{nome}}}} para o nome do lead. Proibido {{{{Cigana}}}}, {{{{assistente}}}} ou qualquer outro placeholder com chaves.
3. Tom místico, acolhedor e direto. Sem pressão agressiva.
4. PROIBIDO mencionar búzios, tremor em búzios ou instrumentos que não sejam a mão/linhas (soa genérico e quebra a personagem da Cigana no WhatsApp).
5. Se for 'recuperacao_1' (5 min): Apenas uma frase mística de 'está por aqui?'.
6. Se for 'recuperacao_2' (1 hora): Reforce que você parou sua vida no altar por ele.
7. Se for 'recuperacao_3' (3 horas): Despedida respeitosa, portal fechando por falta de troca.

Retorne APENAS o texto da mensagem final."""

        try:
            res = self.client.models.generate_content(
                model=self.model_name,
                contents=f"SISTEMA:\n{system_instruction}\n\nUSUÁRIO:\n{prompt_usuario}"
            )
            
            corpo = res.text.strip().replace('"', '').replace('```', '')

            # Salva no DB para reutilização e tracking
            db = SessionLocal()
            try:
                tmpl = TemplateMsg(
                    chave_base=chave_base,
                    categoria=categoria,
                    node_origem=node,
                    corpo=corpo,
                    # 🚨 FIX VITAL APLICADO: A linha 'variaveis_detectadas' foi REMOVIDA para não crashar o DB!
                    score_conversao=0.5,
                    total_usos=0,
                    ativo=True,
                    criado_em=datetime.now(timezone.utc),
                )
                db.add(tmpl)
                db.commit()
                logger.info("💾 [REGISTRY] Template '%s' persistido no banco de dados.", chave_base)
            finally:
                db.close()

            self._cache_memoria[chave_base] = corpo
            return corpo

        except Exception as e:
            logger.error("🚨 [REGISTRY] Erro na geração Gemini: %s", e)
            return self._fallback_hardcoded(categoria)

    # ──────────────────────────────────────────
    # AUXILIARES E REGRAS DE NEGÓCIO
    # ──────────────────────────────────────────
    def _node_para_label(self, node: str) -> str:
        """Mapeia os Nodes para contextos amigáveis para a IA."""
        mapa = {
            "1_apresentacao": "apresentação inicial",
            "2_salvar_contato": "momento de salvar o contato (VCard)",
            "3_coleta_profunda": "pedido da foto da palma da mão e desabafo",
            "4_instagram": "antecâmara de prova social no Instagram",
            "5_processa_leitura": "análise interna da IA",
            "6_atencao_dinamica": "revelação da leitura das linhas",
            "7_interesse_desejo": "agitação do problema espiritual",
            "8_oferta_principal": "conclusão do pagamento/firmação por PIX",
        }
        return mapa.get(node, f"etapa '{node}' do funil")

    def _system_por_categoria(self, categoria: str) -> str:
        """Define a diretriz de sistema conforme o tempo de inatividade."""
        systems = {
            "recuperacao_1": "Cigana Esmeralda. Lead parou há 5 min. Cheque a vibração de forma leve.",
            "recuperacao_2": "Cigana Esmeralda. Lead ignorou há 1h. Reacenda o interesse focando no Altar.",
            "recuperacao_3": "Cigana Esmeralda. 3h de vácuo. Despedida digna, portal fechando.",
        }
        return systems.get(categoria, systems["recuperacao_1"])

    def _substituir_variaveis(self, corpo: str, variaveis: dict) -> str:
        """Aplica os dados reais do lead no template."""
        defaults = {"nome": VOCATIVO_SEM_NOME}
        defaults.update(variaveis)
        resultado = corpo
        for k, v in defaults.items():
            resultado = resultado.replace(f"{{{{{k}}}}}", str(v))
        return resultado.strip()

    @staticmethod
    def _sanear_corpo_template_final(texto: str) -> str:
        """Remove placeholders que a IA inventou (ex.: {{Cigana Esmeralda}}) e não foram substituídos."""
        t = (texto or "").strip()
        t = re.sub(r"\{\{[^}]+\}\}", "", t)
        return re.sub(r"\s{2,}", " ", t).strip()

    def _normalizar_node(self, node: str) -> str:
        return node.replace("/", "_").replace(".", "_")[:40]

    def _agendar_refresh(self, chave_base: str, template_antigo):
        """Thread para resetar usos e permitir que a IA gere uma nova variante (A/B Test)."""
        def _refresh():
            try:
                db = SessionLocal()
                tmpl = db.query(TemplateMsg).filter_by(id=template_antigo.id).first()
                if tmpl:
                    tmpl.total_usos = 0 
                    db.commit()
                    logger.info("🔄 [REGISTRY] Ciclo de teste A/B renovado para '%s'.", chave_base)
                db.close()
            except Exception as e:
                logger.error("🚨 [REGISTRY] Falha no refresh A/B: %s", e)
        
        threading.Thread(target=_refresh, daemon=True).start()

    def _registrar_uso(self, chave_base: str):
        """Contabiliza o uso para métricas de conversão futura."""
        db = SessionLocal()
        try:
            tmpl = db.query(TemplateMsg).filter_by(chave_base=chave_base, ativo=True).first()
            if tmpl:
                tmpl.total_usos = (tmpl.total_usos or 0) + 1
                db.commit()
        finally:
            db.close()

    def registrar_conversao(self, chave_base: str):
        """Incrementa o sucesso do template (lead voltou a falar)."""
        db = SessionLocal()
        try:
            tmpl = db.query(TemplateMsg).filter_by(chave_base=chave_base, ativo=True).first()
            if tmpl:
                tmpl.total_conversoes = (tmpl.total_conversoes or 0) + 1
                if tmpl.total_usos > 0:
                    tmpl.score_conversao = tmpl.total_conversoes / tmpl.total_usos
                db.commit()
                self._cache_memoria.pop(chave_base, None) # Limpa cache para atualizar score
                logger.info("🎯 [REGISTRY] Conversão! Score de '%s' subiu para %.2f", chave_base, tmpl.score_conversao)
        finally:
            db.close()

    def _fallback_hardcoded(self, categoria: str) -> str:
        """Rede de segurança se a IA falhar totalmente."""
        if "recuperacao_1" in categoria:
            return "{{nome}}, senti uma mudança na energia... ainda está por aqui? 🔮"
        return "{{nome}}, as cartas ainda estão na mesa esperando por si. ✨"