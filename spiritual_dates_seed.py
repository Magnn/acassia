"""
Seed de datas espirituais (Frente 4.22).

Tradicoes:
    crista        — datas cristas, dia dos santos
    afro          — orixas, terreiros, festas afro-brasileiras
    paga          — wicca/celta/druida (Samhain, Beltane, etc)
    astronomica   — equinocios, solsticios, eclipses
    secular       — datas civis com peso espiritual (mes psicologico, etc)

Uso: python -m spiritual_dates_seed
"""

from __future__ import annotations

import logging

from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)


# ─── Catalogo curado ──────────────────────────────────────────────────


CATALOG: list[dict] = [
    # AFRO-BRASILEIRA (umbanda, candomble)
    {"tradition": "afro", "name": "Iemanja", "month": 2, "day": 2,
     "description": "Dia dedicado a Iemanja, mae das aguas. Oferendas no mar, flores brancas. Energia de cura emocional, maternidade e fluidez."},
    {"tradition": "afro", "name": "Cosme e Damiao", "month": 9, "day": 27,
     "description": "Dia dos Erês — proteção das criancas, alegria, doces. Pedido a saude, juventude e renovacao."},
    {"tradition": "afro", "name": "Oxala", "month": 1, "day": 1,
     "description": "Dia de Oxala, pai da criacao. Energia de paz, sabedoria, recomeco. Vela branca, frutas brancas."},
    {"tradition": "afro", "name": "Sao Jorge / Ogum", "month": 4, "day": 23,
     "description": "Sao Jorge guerreiro, sincretizado com Ogum. Protecao, abertura de caminhos, vitoria sobre obstaculos."},
    {"tradition": "afro", "name": "Iansa / Santa Barbara", "month": 12, "day": 4,
     "description": "Iansa dos ventos e tempestades, sincretizada com Santa Barbara. Protecao contra raios, coragem, transformacao rapida."},
    {"tradition": "afro", "name": "Oxossi / Sao Sebastiao", "month": 1, "day": 20,
     "description": "Oxossi cacador, sincretizado com Sao Sebastiao. Abundancia, prosperidade, protecao da floresta."},
    {"tradition": "afro", "name": "Xango / Sao Joao", "month": 6, "day": 24,
     "description": "Xango da justica, sincretizado com Sao Joao. Energia de fogo, decisoes firmes, justica divina."},

    # CRISTA
    {"tradition": "crista", "name": "Dia de Reis", "month": 1, "day": 6,
     "description": "Epifania — chegada dos tres reis magos. Encerramento das festas natalinas, recomeco do ano espiritual."},
    {"tradition": "crista", "name": "Pascoa", "recurring": "annual_movable",
     "description": "Pascoa crista — domingo apos primeira lua cheia depois do equinocio de marco. Energia de ressurreicao e renovacao."},
    {"tradition": "crista", "name": "Quarta-feira de Cinzas", "recurring": "annual_movable",
     "description": "Inicio da Quaresma. 46 dias antes da Pascoa. Tempo de jejum, oracao, reflexao."},
    {"tradition": "crista", "name": "Pentecostes", "recurring": "annual_movable",
     "description": "50 dias apos a Pascoa. Dia do Espirito Santo. Renovacao espiritual, dons, linguas."},
    {"tradition": "crista", "name": "Corpus Christi", "recurring": "annual_movable",
     "description": "60 dias apos a Pascoa. Celebracao da Eucaristia. Energia de comunhao."},
    {"tradition": "crista", "name": "Nossa Senhora Aparecida", "month": 10, "day": 12,
     "description": "Padroeira do Brasil. Dia de devocao mariana. Pedidos de protecao familiar."},
    {"tradition": "crista", "name": "Finados", "month": 11, "day": 2,
     "description": "Dia dos mortos. Honrar antepassados, visitas a tumulos, oracao pelos que partiram."},
    {"tradition": "crista", "name": "Santo Antonio", "month": 6, "day": 13,
     "description": "Padroeiro dos casamentos e das coisas perdidas. Simpatias para encontrar amor ou objetos."},

    # PAGA / CELTA / WICCA
    {"tradition": "paga", "name": "Samhain", "month": 4, "day": 30,
     "description": "(Hemisferio sul) — vespera do nosso 'ano novo' bruxo. Veu entre mundos fino, ancestrais, divinacao. No norte e 31/10."},
    {"tradition": "paga", "name": "Beltane", "month": 10, "day": 31,
     "description": "(Hemisferio sul) — festival da fertilidade e do amor. No norte e 30/4. Fogueiras, dancas, casamento sagrado."},
    {"tradition": "paga", "name": "Imbolc", "month": 8, "day": 1,
     "description": "(Hemisferio sul) — primeiros sinais da primavera, retorno da luz. Renovacao, purificacao, nova fase."},
    {"tradition": "paga", "name": "Lammas/Lughnasadh", "month": 2, "day": 1,
     "description": "(Hemisferio sul) — festa da primeira colheita. Gratidao, abundancia, reconhecer fruto do trabalho."},

    # ASTRONOMICA (hemisferio sul)
    {"tradition": "astronomica", "name": "Equinocio de outono", "month": 3, "day": 20,
     "description": "Hemisferio sul. Dia e noite igualam. Equilibrio entre luz e escuridao. Tempo de balancos."},
    {"tradition": "astronomica", "name": "Solsticio de inverno", "month": 6, "day": 21,
     "description": "Hemisferio sul. Noite mais longa. Introspeccao profunda, semente em silencio."},
    {"tradition": "astronomica", "name": "Equinocio de primavera", "month": 9, "day": 22,
     "description": "Hemisferio sul. Renascer da luz. Plantar, comecar projetos novos."},
    {"tradition": "astronomica", "name": "Solsticio de verao", "month": 12, "day": 21,
     "description": "Hemisferio sul. Dia mais longo. Festa do Sol, energia maxima, celebracao."},
    {"tradition": "astronomica", "name": "Marte retrogrado", "recurring": "annual_movable",
     "description": "Periodo de revisao em acoes, pausa antes de avancar. Cuidado com decisoes impulsivas."},

    # SECULAR (peso espiritual reconhecido)
    {"tradition": "secular", "name": "Janeiro Branco", "month": 1, "day": 1,
     "description": "Mes da saude mental. Reflexao sobre proprias questoes psicologicas."},
    {"tradition": "secular", "name": "Setembro Amarelo", "month": 9, "day": 1,
     "description": "Mes da prevencao do suicidio. Falar sobre dor, oferecer escuta. Energia delicada de cuidado."},
    {"tradition": "secular", "name": "Dia das Maes (BR)", "month": 5, "day": 13,
     "description": "Segundo domingo de maio. Dia 13 e referencia; data exata varia."},
    {"tradition": "secular", "name": "Dia dos Pais (BR)", "month": 8, "day": 11,
     "description": "Segundo domingo de agosto. Dia 11 e referencia; data exata varia."},
    {"tradition": "secular", "name": "Dia dos Namorados", "month": 6, "day": 12,
     "description": "Vespera de Santo Antonio (BR). Energia de amor romantico, presentes e declaracoes."},
]


def seed(*, force: bool = False) -> dict:
    """Insere o catalogo se ainda nao existir. Retorna {inserted, skipped}."""
    db = SessionLocal()
    inserted = 0
    skipped = 0
    try:
        if force:
            db.query(models.SpiritualDate).filter(
                models.SpiritualDate.tenant_id.is_(None),
            ).delete()
            db.commit()

        for entry in CATALOG:
            tradition = entry["tradition"]
            name = entry["name"]
            existing = db.query(models.SpiritualDate).filter_by(
                tradition=tradition, name=name, tenant_id=None,
            ).first()
            if existing:
                skipped += 1
                continue
            db.add(models.SpiritualDate(
                tradition=tradition,
                name=name,
                description=entry.get("description"),
                recurring=entry.get("recurring", "annual_fixed"),
                month=entry.get("month"),
                day=entry.get("day"),
                tenant_id=None,
            ))
            inserted += 1

        if inserted:
            db.commit()
        return {"inserted": inserted, "skipped": skipped}
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")
    import sys
    force = "--force" in sys.argv
    result = seed(force=force)
    print(f"Inserted: {result['inserted']} · Skipped: {result['skipped']}")
