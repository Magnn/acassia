"""
Seed do deck Marselha completo (78 cartas) — Frente 4.7.

Idempotente — executar várias vezes não duplica.
Run: python -m tarot_seed
"""

from __future__ import annotations

import logging

from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)


# Arcanos maiores (22 cartas)
MAJOR_ARCANA = [
    {"id": "0_louco", "number": 0, "name": "O Louco",
     "upright": "Liberdade, novos começos, espontaneidade, fé no caminho.",
     "reversed": "Imprudência, escolhas precipitadas, irresponsabilidade.",
     "keywords": ["aventura", "início", "inocência", "salto"]},
    {"id": "1_mago", "number": 1, "name": "O Mago",
     "upright": "Manifestação, poder pessoal, foco, ação consciente.",
     "reversed": "Manipulação, talentos não usados, ilusão.",
     "keywords": ["poder", "criação", "vontade", "habilidade"]},
    {"id": "2_papisa", "number": 2, "name": "A Papisa",
     "upright": "Intuição, mistério, sabedoria interior, espiritualidade.",
     "reversed": "Segredos guardados, isolamento, intuição reprimida.",
     "keywords": ["sabedoria", "intuição", "silêncio", "mistério"]},
    {"id": "3_imperatriz", "number": 3, "name": "A Imperatriz",
     "upright": "Fertilidade, abundância, mãe-natureza, criação.",
     "reversed": "Bloqueio criativo, dependência, excesso.",
     "keywords": ["abundância", "fertilidade", "criação", "amor"]},
    {"id": "4_imperador", "number": 4, "name": "O Imperador",
     "upright": "Estrutura, autoridade, controle, estabilidade.",
     "reversed": "Tirania, rigidez, autoridade abusiva.",
     "keywords": ["liderança", "estrutura", "ordem", "pai"]},
    {"id": "5_papa", "number": 5, "name": "O Papa",
     "upright": "Tradição, conformidade, fé, ensino espiritual.",
     "reversed": "Rebeldia, dogmatismo, hipocrisia.",
     "keywords": ["tradição", "fé", "guia", "ensino"]},
    {"id": "6_amorosos", "number": 6, "name": "Os Amantes",
     "upright": "Amor, escolhas, união, alinhamento.",
     "reversed": "Desalinhamento, escolhas erradas, separação.",
     "keywords": ["amor", "escolha", "união", "harmonia"]},
    {"id": "7_carro", "number": 7, "name": "O Carro",
     "upright": "Vitória, determinação, controle, vontade.",
     "reversed": "Falta de direção, agressividade, derrota.",
     "keywords": ["vitória", "movimento", "vontade", "conquista"]},
    {"id": "8_justica", "number": 8, "name": "A Justiça",
     "upright": "Equilíbrio, verdade, lei, julgamento justo.",
     "reversed": "Injustiça, desonestidade, desequilíbrio.",
     "keywords": ["equilíbrio", "verdade", "justiça", "lei"]},
    {"id": "9_eremita", "number": 9, "name": "O Eremita",
     "upright": "Introspecção, busca interior, sabedoria, solidão escolhida.",
     "reversed": "Isolamento, retirada excessiva, paranoia.",
     "keywords": ["introspecção", "busca", "luz", "guia"]},
    {"id": "10_roda", "number": 10, "name": "A Roda da Fortuna",
     "upright": "Mudança, ciclos, destino, sorte.",
     "reversed": "Má sorte, ciclo negativo, falta de controle.",
     "keywords": ["destino", "ciclo", "mudança", "fortuna"]},
    {"id": "11_forca", "number": 11, "name": "A Força",
     "upright": "Coragem, paciência, controle gentil, força interior.",
     "reversed": "Fraqueza, dúvida, falta de autoconfiança.",
     "keywords": ["coragem", "paciência", "força", "compaixão"]},
    {"id": "12_enforcado", "number": 12, "name": "O Enforcado",
     "upright": "Pausa, sacrifício, novo ponto de vista, espera.",
     "reversed": "Resistência à mudança, atraso, sacrifício inútil.",
     "keywords": ["pausa", "perspectiva", "sacrifício", "rendição"]},
    {"id": "13_morte", "number": 13, "name": "A Morte",
     "upright": "Transformação, fim de ciclo, renascimento, mudança profunda.",
     "reversed": "Resistência à mudança, estagnação, medo.",
     "keywords": ["transformação", "fim", "renascimento", "mudança"]},
    {"id": "14_temperanca", "number": 14, "name": "A Temperança",
     "upright": "Equilíbrio, moderação, paciência, harmonia.",
     "reversed": "Desequilíbrio, excesso, falta de visão.",
     "keywords": ["equilíbrio", "moderação", "paciência", "harmonia"]},
    {"id": "15_diabo", "number": 15, "name": "O Diabo",
     "upright": "Apego, ilusão, materialismo, vícios.",
     "reversed": "Libertação, quebra de correntes, recuperação.",
     "keywords": ["apego", "ilusão", "tentação", "materialismo"]},
    {"id": "16_torre", "number": 16, "name": "A Torre",
     "upright": "Mudança súbita, ruptura, revelação, libertação dolorosa.",
     "reversed": "Crise evitada, medo de mudança, ruptura interna.",
     "keywords": ["ruptura", "revelação", "queda", "liberdade"]},
    {"id": "17_estrela", "number": 17, "name": "A Estrela",
     "upright": "Esperança, fé, renovação, inspiração.",
     "reversed": "Desesperança, falta de fé, desânimo.",
     "keywords": ["esperança", "fé", "inspiração", "luz"]},
    {"id": "18_lua", "number": 18, "name": "A Lua",
     "upright": "Intuição, ilusão, sonhos, subconsciente.",
     "reversed": "Confusão, medo, ansiedade, autoengano.",
     "keywords": ["intuição", "sonho", "mistério", "ilusão"]},
    {"id": "19_sol", "number": 19, "name": "O Sol",
     "upright": "Sucesso, alegria, vitalidade, clareza.",
     "reversed": "Tristeza temporária, falta de entusiasmo, ego.",
     "keywords": ["sucesso", "alegria", "vitalidade", "luz"]},
    {"id": "20_julgamento", "number": 20, "name": "O Julgamento",
     "upright": "Renascimento, despertar, perdão, segunda chance.",
     "reversed": "Auto-julgamento, dúvida, oportunidade perdida.",
     "keywords": ["despertar", "renovação", "perdão", "decisão"]},
    {"id": "21_mundo", "number": 21, "name": "O Mundo",
     "upright": "Conclusão, plenitude, realização, integração.",
     "reversed": "Conclusão incompleta, falta de fechamento.",
     "keywords": ["conclusão", "plenitude", "sucesso", "integração"]},
]


# Naipes menores (4 naipes × 14 cartas = 56)
SUITS = [
    {"key": "copas", "name": "Copas", "theme": "emoções, amor, relacionamentos, intuição"},
    {"key": "ouros", "name": "Ouros", "theme": "dinheiro, trabalho, prosperidade material"},
    {"key": "espadas", "name": "Espadas", "theme": "mente, conflito, decisões, intelecto"},
    {"key": "paus", "name": "Paus", "theme": "ação, paixão, criatividade, carreira"},
]


def _gen_minor_arcana():
    cards = []
    for suit in SUITS:
        for n in range(1, 11):
            name_n = "Ás" if n == 1 else str(n)
            cards.append({
                "id": f"{suit['key']}_{n}",
                "number": n,
                "name": f"{name_n} de {suit['name']}",
                "suit": suit["key"],
                "upright": f"Energia inicial de {suit['theme']}." if n == 1
                           else f"Etapa {n} no caminho de {suit['theme']}.",
                "reversed": f"Bloqueio ou desafio em {suit['theme']}.",
                "keywords": suit["theme"].split(", "),
            })
        # Cortes
        for figure in ["valete", "cavaleiro", "rainha", "rei"]:
            cards.append({
                "id": f"{suit['key']}_{figure}",
                "name": f"{figure.capitalize()} de {suit['name']}",
                "suit": suit["key"],
                "number": None,
                "upright": f"Personalidade arquetípica de {suit['theme']}.",
                "reversed": f"Sombra arquetípica relacionada a {suit['theme']}.",
                "keywords": [figure, suit["key"]],
            })
    return cards


MARSELHA_DECK_ID = "marselha"


def seed():
    db = SessionLocal()
    inserted = 0
    updated = 0
    try:
        # Cria o deck
        deck = db.query(models.TarotDeck).filter_by(id=MARSELHA_DECK_ID).first()
        if not deck:
            deck = models.TarotDeck(
                id=MARSELHA_DECK_ID,
                name="Tarot de Marselha (clássico)",
                is_default=True,
                tenant_id=None,  # global
            )
            db.add(deck)
            inserted += 1

        # Major arcana
        for card_data in MAJOR_ARCANA:
            existing = db.query(models.TarotCard).filter_by(
                id=card_data["id"], deck_id=MARSELHA_DECK_ID,
            ).first()
            if existing:
                existing.name = card_data["name"]
                existing.meaning_upright = card_data["upright"]
                existing.meaning_reversed = card_data["reversed"]
                existing.keywords = card_data["keywords"]
                updated += 1
            else:
                db.add(models.TarotCard(
                    id=card_data["id"],
                    deck_id=MARSELHA_DECK_ID,
                    name=card_data["name"],
                    arcana="major",
                    suit=None,
                    number=card_data.get("number"),
                    meaning_upright=card_data["upright"],
                    meaning_reversed=card_data["reversed"],
                    keywords=card_data["keywords"],
                ))
                inserted += 1

        # Minor arcana
        for card_data in _gen_minor_arcana():
            existing = db.query(models.TarotCard).filter_by(
                id=card_data["id"], deck_id=MARSELHA_DECK_ID,
            ).first()
            if existing:
                existing.name = card_data["name"]
                existing.meaning_upright = card_data["upright"]
                existing.meaning_reversed = card_data["reversed"]
                updated += 1
            else:
                db.add(models.TarotCard(
                    id=card_data["id"],
                    deck_id=MARSELHA_DECK_ID,
                    name=card_data["name"],
                    arcana="minor",
                    suit=card_data["suit"],
                    number=card_data.get("number"),
                    meaning_upright=card_data["upright"],
                    meaning_reversed=card_data["reversed"],
                    keywords=card_data.get("keywords") or [],
                ))
                inserted += 1
        db.commit()
        logger.info("[tarot_seed] inserted=%d updated=%d", inserted, updated)
        return inserted, updated
    finally:
        db.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    inserted, updated = seed()
    print(f"Inserted: {inserted}, Updated: {updated}")
