"""
schema.py — Contrato Central de Dados (SUPREME v2.2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Define as estruturas de dados fundamentais (Acao e ContextoConversa)
em um arquivo neutro e isolado.

APRIMORAMENTOS:
🔥 TYPE HINTING EXTENDIDO: Detalhes e valores default para mais clareza.
🔥 FIX DATACLASS: Reordenação estrita mantendo 'texto_recebido' antes dos campos default.
🔥 ROBUSTEZ DE DADOS: Assegura que os tipos e as descrições sejam respeitados.
"""

from dataclasses import dataclass, field
from typing import Any, Optional, List, Dict

@dataclass
class Acao:
    """
    Representa uma ação unitária que a Cigana (bot) deve executar.
    """
    tipo: str = field(
        default="",
        metadata={"description": "Tipo da ação: text, interactive, audio, image, vcard, delay, tts"}
    )
    conteudo: str = field(
        default="",
        metadata={"description": "Texto da mensagem, número do vcard, etc."}
    )
    url: str = field(
        default="",
        metadata={"description": "URL para mídias externas (áudio, imagem)"}
    )
    segundos: int = field(
        default=0,
        metadata={"description": "Tempo de delay/espera em segundos"}
    )
    tts_template: str = field(
        default="",
        metadata={"description": "Template de texto que será convertido em voz"}
    )
    metadata: Dict[str, Any] = field(
        default_factory=dict,
        metadata={"description": "Dados extras da ação"}
    )


@dataclass
class ContextoConversa:
    """
    Objeto de estado transiente. Carrega toda a inteligência e memória
    da sessão atual para ser processada e enriquecida pelos Nodes.
    """
    # ── 1. CAMPOS OBRIGATÓRIOS (Sem default - Devem ficar estritamente no topo) ──
    lead_id: int = field(
        metadata={"description": "ID único do lead no banco de dados"}
    )
    telefone: str = field(
        metadata={"description": "Número de telefone do lead"}
    )
    node_atual: str = field(
        metadata={"description": "ID do nó atual do fluxo de conversa"}
    )
    texto_recebido: str = field(
        metadata={"description": "Texto da mensagem recebida do lead"}
    )

    # ── 2. CAMPOS OPCIONAIS / COM DEFAULT (Devem ficar abaixo) ──
    tipo_mensagem: str = field(
        default="text",
        metadata={"description": "Tipo da mensagem: text, audio, image, etc."}
    )
    historico: List[Any] = field(
        default_factory=list,
        metadata={"description": "Histórico de mensagens (objetos SQLAlchemy ou dicts)"}
    )
    interactive_reply_id: Optional[str] = field(
        default=None,
        metadata={"description": "ID da resposta interativa (se houver)"}
    )

    # ── Inteligência Emocional (Preenchida pelo Engine) ──
    nome_lead: str = field(
        default="",
        metadata={"description": "Nome do lead (extraído da conversa)"}
    )
    intencao: str = field(
        default="indefinida",
        metadata={"description": "Intenção do lead (classificada pela IA)"}
    )
    sentimento: str = field(
        default="padrao",
        metadata={"description": "Sentimento do lead (analisado pela IA)"}
    )
    score_engajamento: float = field(
        default=0.5,
        metadata={"description": "Score de engajamento do lead (analisado pela IA)"}
    )

    # ── Dependências e Estado de Máquina ──
    personalizer: Any = field(
        default=None,
        metadata={"description": "Instância da IA (Personalizer)"}
    )
    estado_coleta: str = field(
        default="inicial",
        metadata={"description": "Estado da coleta de informações (inicial, etc.)"}
    )

    # ── Metadados Dinâmicos (Dores, Desejos, Configurações .env) ──
    metadata: Dict[str, Any] = field(
        default_factory=dict,
        metadata={"description": "Metadados dinâmicos (dores, desejos, configurações)"}
    )


def slice_historico_para_ia(ctx: ContextoConversa, limite: int = 20) -> List[Any]:
    """Últimas mensagens para o Personalizer — evita chamar a IA sem contexto."""
    h = ctx.historico or []
    if not h:
        return []
    return h[-limite:] if len(h) > limite else h