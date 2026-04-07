from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from config_cliente import CONFIG_CLIENTE
from schema import ContextoConversa
from flows.fase_1_saudacao import node_2_salvar_contato


class _PersonalizerMock:
    def gerar_resposta(self, **kwargs):
        return (
            "Primeiro balão muito explicativo e acolhedor para confirmar o contexto do lead [BALAO] "
            "Segundo balão também grande para simular possível excesso de verbosidade antes de encurtar [BALAO] "
            "Posso seguir com você agora para o próximo passo da leitura das linhas?"
        )


def _ctx(texto: str, meta: dict | None = None) -> ContextoConversa:
    m = {"__config__": CONFIG_CLIENTE}
    if meta:
        m.update(meta)
    return ContextoConversa(
        lead_id=999002,
        telefone="+5592999999999",
        node_atual="2_salvar_contato",
        texto_recebido=texto,
        nome_lead=str(m.get("nome_lead") or "Magno"),
        metadata=m,
        personalizer=None,
    )


def _txt(acoes):
    return [a.conteudo for a in acoes if getattr(a, "tipo", "") == "text"]


def run() -> int:
    erros: list[str] = []

    # 1) já salvei => fast-track sem pedir salvar de novo
    c1 = _ctx("já salvei seu contato", {"lead_contato_salvo_declarado": True})
    a1, p1 = node_2_salvar_contato.executar_v2(c1)
    t1 = " ".join(_txt(a1)).lower()
    if p1 != "3_coleta_profunda":
        erros.append("c1: deveria ir para 3_coleta_profunda")
    if "salva meu contato" in t1:
        erros.append("c1: repetiu pedido para salvar contato")

    # 2) objeção de card => reenvia card e permanece no node2
    c2 = _ctx("não achei seu contato")
    a2, p2 = node_2_salvar_contato.executar_v2(c2)
    if p2 != "2_salvar_contato":
        erros.append("c2: deveria permanecer no node2")
    if not any(getattr(a, "tipo", "") == "vcard" for a in a2):
        erros.append("c2: não reenviou vcard")

    # 3) um turno = uma pergunta no máximo
    perguntas = 0
    for t in _txt(a2):
        perguntas += t.count("?")
    if perguntas > 1:
        erros.append("c2: mais de uma pergunta no mesmo turno")

    # 4) caps gerais
    for nome, acoes in (("c1", a1), ("c2", a2)):
        for t in _txt(acoes):
            if len(t) > 210:
                erros.append(f"{nome}: balao acima de 210 chars")

    # 5) caminho com IA mock: mantém cap e pergunta única
    c3 = _ctx("estou em dúvida e com pressa", {"nome_lead": "Magno"})
    c3.personalizer = _PersonalizerMock()
    a3, _ = node_2_salvar_contato.executar_v2(c3)
    txt3 = _txt(a3)
    if not txt3:
        erros.append("c3: sem texto no caminho IA mock")
    if any(len(t) > 210 for t in txt3):
        erros.append("c3: cap de 210 falhou no caminho IA mock")
    perguntas3 = sum(t.count("?") for t in txt3)
    if perguntas3 > 1:
        erros.append("c3: mais de uma pergunta no caminho IA mock")

    if erros:
        print("NODE2 GUARDRAILS FAIL")
        for e in erros:
            print("-", e)
        return 1
    print("NODE2 GUARDRAILS OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(run())

