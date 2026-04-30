"""
Seed do glossario espiritual (Frente 4.21).

Termos PT-BR curados pra evitar alucinacao do GPT em contextos espirituais.
Inserido como global (tenant_id=null) — tenants podem adicionar custom por
cima via /saas/glossary.

Uso: python -m spiritual_glossary_seed
"""

from __future__ import annotations

import logging

from db import models
from db.database import SessionLocal


logger = logging.getLogger(__name__)


GLOSSARY: list[dict] = [
    # ─── Afro-brasileira (uso tecnico, sempre respeitoso) ─────────────
    {"term": "Orixa", "category": "afro", "importance": 10,
     "definition": "Divindade da tradicao afro-brasileira (Candomble, Umbanda). NUNCA confundir com 'guia' generico. Cada Orixa tem nome, dominio e cores especificas (Iansa = ventos, Iemanja = aguas, Xango = fogo/justica, etc)."},
    {"term": "Iemanja", "category": "afro", "importance": 9,
     "definition": "Orixa das aguas salgadas, mae mistica. Dia 2/2. Cores azul claro e branco. Nao confundir com Iansa."},
    {"term": "Iansa", "category": "afro", "importance": 9,
     "definition": "Orixa dos ventos e tempestades, sincretizada com Santa Barbara. Dia 4/12. Cores vermelho/coral. Energia de transformacao rapida e coragem. NAO e Iemanja."},
    {"term": "Ogum", "category": "afro", "importance": 8,
     "definition": "Orixa guerreiro, abridor de caminhos. Sincretizado com Sao Jorge (23/4). Cor verde escuro/vermelho. Energia de conquista e protecao."},
    {"term": "Oxum", "category": "afro", "importance": 8,
     "definition": "Orixa das aguas doces (rios, cachoeiras), maternidade, fertilidade, beleza. Cor amarelo-ouro. Sincretizada com Nossa Senhora Aparecida."},
    {"term": "Pomba-gira", "category": "afro", "importance": 9,
     "definition": "Entidade feminina da Umbanda, lado da esquerda, especialista em amor, sensualidade, problemas de relacionamento. SEMPRE tratada com respeito; nao e demonio. Vermelho/preto sao cores associadas."},
    {"term": "Exu", "category": "afro", "importance": 9,
     "definition": "Mensageiro, abridor de caminhos. NUNCA confundir com 'demonio' do cristianismo. Forca de transformacao, comunicacao entre planos."},
    {"term": "Preto-Velho", "category": "afro", "importance": 8,
     "definition": "Espirito de ancestral africano, sabio, paciente. Trabalha na Umbanda dando consolo, cura, conselho. Tem nome proprio (Pai Joao, Vovo Maria, etc)."},
    {"term": "Caboclo", "category": "afro", "importance": 7,
     "definition": "Espirito de indigena brasileiro, na Umbanda. Trabalha com forcas da natureza, cura por ervas. Tem nome proprio (Caboclo Pena Branca, Cobra Coral, etc)."},
    {"term": "Saravá", "category": "afro", "importance": 7,
     "definition": "Saudacao reverencial nas religioes afro-brasileiras. 'Saravá Ogum!' = saudo Ogum. Equivale a 'Salve!'."},
    {"term": "Axé", "category": "afro", "importance": 9,
     "definition": "Forca vital, energia sagrada das tradicoes afro. 'Que axe!' = expressao de aprovacao espiritual. NAO e bencao crista."},
    {"term": "Egum", "category": "afro", "importance": 7,
     "definition": "Espirito de morto desencarnado, ancestral. NAO e 'agua' (erro comum). Em algumas tradicoes precisa ser cuidado/encaminhado."},
    {"term": "Terreiro", "category": "afro", "importance": 6,
     "definition": "Templo das religioes afro-brasileiras. Espaco sagrado de culto. Casa de santo."},
    {"term": "Mae de Santo", "category": "afro", "importance": 6,
     "definition": "Sacerdotisa iniciada no Candomble/Umbanda. Lidera o terreiro, conduz iniciacoes."},
    {"term": "Ebó", "category": "afro", "importance": 7,
     "definition": "Oferenda ritualistica feita a Orixas. Sempre conduzida por iniciado. NUNCA prescrever pra leigo sem fundamento."},

    # ─── Tarot ────────────────────────────────────────────────────────
    {"term": "Arcano Maior", "category": "tarot", "importance": 9,
     "definition": "As 22 cartas principais do tarot, numeradas 0-21. Representam grandes etapas da jornada da alma: O Louco, O Mago, A Sacerdotisa, O Imperador, etc."},
    {"term": "Arcano Menor", "category": "tarot", "importance": 8,
     "definition": "As 56 cartas dos 4 naipes (Espadas, Copas, Ouros, Paus). Representam situacoes do dia-a-dia."},
    {"term": "Carta invertida", "category": "tarot", "importance": 8,
     "definition": "Carta sai virada de cabeca pra baixo. Significado oposto ou bloqueado da carta em pe. Nem sempre negativo — as vezes alerta de algo a integrar."},
    {"term": "Tiragem", "category": "tarot", "importance": 7,
     "definition": "Ato de embaralhar e abrir as cartas. Tipos comuns: 1 carta (mensagem), 3 cartas (passado-presente-futuro), 5 (cruz), 10 (cruz celta)."},
    {"term": "Cruz Celta", "category": "tarot", "importance": 8,
     "definition": "Tiragem clássica de 10 cartas em formato de cruz. Cada posicao tem significado especifico (presente, obstaculo, raiz, etc)."},
    {"term": "Marselha", "category": "tarot", "importance": 7,
     "definition": "Deck classico de tarot frances, simbologia tradicional. Diferente do Rider-Waite (mais moderno, com cenas)."},
    {"term": "A Estrela", "category": "tarot", "importance": 7,
     "definition": "Arcano XVII. Esperanca, cura, renascimento apos crise. Carta muito positiva."},
    {"term": "A Torre", "category": "tarot", "importance": 7,
     "definition": "Arcano XVI. Ruptura abrupta, queda do que era falso. Nao necessariamente catastrofe — as vezes libertacao."},
    {"term": "O Louco", "category": "tarot", "importance": 7,
     "definition": "Arcano 0. Comeco de jornada, fe ingenua, salto no desconhecido. Pode invertido virar irresponsabilidade."},
    {"term": "Os Amantes", "category": "tarot", "importance": 7,
     "definition": "Arcano VI. Escolha amorosa, uniao, mas tambem decisao etica. Nao e necessariamente amor romantico."},

    # ─── Astrologia ───────────────────────────────────────────────────
    {"term": "Ascendente", "category": "astrologia", "importance": 9,
     "definition": "Signo que estava no horizonte na hora exata do nascimento. Define a 'mascara social', primeira impressao. NAO e o signo solar."},
    {"term": "Signo solar", "category": "astrologia", "importance": 9,
     "definition": "O signo conhecido popularmente, baseado na data de nascimento. Representa identidade central."},
    {"term": "Signo lunar", "category": "astrologia", "importance": 8,
     "definition": "Onde a Lua estava no nascimento. Define mundo emocional, intuicao, relacao com a mae."},
    {"term": "Casa astrologica", "category": "astrologia", "importance": 8,
     "definition": "12 setores do mapa, cada um regendo uma area da vida (1=identidade, 7=parcerias, 10=carreira, etc)."},
    {"term": "Aspecto", "category": "astrologia", "importance": 7,
     "definition": "Angulo entre 2 planetas no mapa. Conjuncao (0°), oposicao (180°), trigono (120°), quadratura (90°), sextil (60°)."},
    {"term": "Trânsito", "category": "astrologia", "importance": 8,
     "definition": "Movimento atual de um planeta, ativando areas do mapa natal. Ex: 'Saturno em transito sobre seu Sol' = momento de prova/maturacao."},
    {"term": "Mercurio retrogrado", "category": "astrologia", "importance": 9,
     "definition": "Periodo de 3 semanas (3-4x ao ano) onde Mercurio aparece andando para tras. Comunicacao confusa, revisitar decisoes, atrasos. NAO 'tudo da errado' — momento de revisao."},
    {"term": "Lua nova", "category": "astrologia", "importance": 8,
     "definition": "Inicio de novo ciclo lunar (~29.5 dias). Bom pra plantar intencoes, comecos."},
    {"term": "Lua cheia", "category": "astrologia", "importance": 8,
     "definition": "Pico da iluminacao lunar. Manifestacao, revelacao, intensidade emocional."},
    {"term": "Eclipse", "category": "astrologia", "importance": 8,
     "definition": "Conjunto Sol-Lua-Terra raro. Marca portais de transformacao acelerada. Nao 'ler tarot' durante (algumas tradicoes)."},

    # ─── Crista / generica ────────────────────────────────────────────
    {"term": "Anjo da guarda", "category": "geral", "importance": 7,
     "definition": "Espirito protetor pessoal, na tradicao crista. Acompanha desde o nascimento."},
    {"term": "Trono", "category": "geral", "importance": 6,
     "definition": "Hierarquia angelica elevada. Tambem usado como 'guia espiritual elevado' em algumas tradicoes."},
    {"term": "Querubim", "category": "geral", "importance": 5,
     "definition": "Ordem angelica de protecao e sabedoria."},

    # ─── Espirita / Kardec ────────────────────────────────────────────
    {"term": "Mediunidade", "category": "espirita", "importance": 8,
     "definition": "Sensibilidade pra perceber/comunicar com plano espiritual. NAO e doenca; e capacidade que precisa ser educada."},
    {"term": "Encosto", "category": "espirita", "importance": 7,
     "definition": "Espirito sofredor que se aproxima de pessoa viva. Necessita desobsessao com prece e estudo, nao 'descarrego'."},
    {"term": "Desobsessao", "category": "espirita", "importance": 7,
     "definition": "Trabalho espirita pra ajudar tanto encarnado quanto desencarnado a se desligarem. Caridade espiritual."},
    {"term": "Vibracao", "category": "espirita", "importance": 7,
     "definition": "Frequencia energetica de pensamentos e emocoes. 'Vibracao positiva' atrai semelhantes."},
    {"term": "Karma", "category": "geral", "importance": 8,
     "definition": "Lei de causa e efeito moral, doutrina do oriente assimilada no espiritismo. NAO 'castigo divino' — aprendizagem."},

    # ─── Holistica / energetica ──────────────────────────────────────
    {"term": "Chakra", "category": "holistica", "importance": 8,
     "definition": "Centro energetico do corpo na tradicao indiana. 7 principais: raiz, sacro, plexo, coracao, garganta, frontal, coronario."},
    {"term": "Reiki", "category": "holistica", "importance": 7,
     "definition": "Tecnica japonesa de canalizacao de energia universal pelas maos. Pratica complementar, nao substitui medicina."},
    {"term": "Aura", "category": "holistica", "importance": 7,
     "definition": "Campo energetico ao redor do corpo. Cores variam segundo estado emocional/espiritual."},

    # ─── Ciganos ──────────────────────────────────────────────────────
    {"term": "Romani", "category": "cigana", "importance": 6,
     "definition": "Povo cigano (auto-denominacao). Cultura nomade com tradicoes de vidência."},
    {"term": "Sara Kali", "category": "cigana", "importance": 6,
     "definition": "Santa cigana, padroeira. Devocao popular entre povo Romani."},

    # ─── Numerologia ──────────────────────────────────────────────────
    {"term": "Numero da Vida", "category": "numerologia", "importance": 8,
     "definition": "Calculado da data de nascimento. Reduz soma a 1-9 (mestres 11/22/33 nao reduzem). Define ciclo principal de aprendizado."},
    {"term": "Numero Mestre", "category": "numerologia", "importance": 7,
     "definition": "11, 22 e 33 — nao se reduzem. Energias amplificadas com missao espiritual."},
]


def seed(*, force: bool = False) -> dict:
    db = SessionLocal()
    inserted = 0
    skipped = 0
    try:
        if force:
            db.query(models.SpiritualGlossaryTerm).filter(
                models.SpiritualGlossaryTerm.tenant_id.is_(None),
            ).delete()
            db.commit()

        for entry in GLOSSARY:
            existing = db.query(models.SpiritualGlossaryTerm).filter_by(
                tenant_id=None, term=entry["term"],
            ).first()
            if existing:
                skipped += 1
                continue
            db.add(models.SpiritualGlossaryTerm(
                tenant_id=None,
                term=entry["term"],
                definition=entry["definition"],
                category=entry.get("category"),
                importance=entry.get("importance", 5),
                usage_examples=entry.get("usage_examples"),
            ))
            inserted += 1

        if inserted:
            db.commit()
        return {"inserted": inserted, "skipped": skipped, "total": len(GLOSSARY)}
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")
    force = "--force" in sys.argv
    result = seed(force=force)
    print(f"Inserted: {result['inserted']}, Skipped: {result['skipped']}, "
          f"Total seed: {result['total']}")
