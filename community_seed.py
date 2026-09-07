"""
community_seed.py — Seed de grupos default da comunidade por signo zodiacal.
Cria 12 grupos por signo + 4 grupos temáticos se não existirem.
"""
from db.database import SessionLocal
from db import models


DEFAULT_GROUPS = [
    # Por signo
    {"name": "Círculo de Áries", "slug": "aries", "category": "signo", "icon": "♈",
     "description": "Guerreiros do fogo: coragem, ação e liderança."},
    {"name": "Círculo de Touro", "slug": "touro", "category": "signo", "icon": "♉",
     "description": "Guardiões da terra: estabilidade, prazer e abundância."},
    {"name": "Círculo de Gêmeos", "slug": "gemeos", "category": "signo", "icon": "♊",
     "description": "Mensageiros do ar: comunicação, curiosidade e versatilidade."},
    {"name": "Círculo de Câncer", "slug": "cancer", "category": "signo", "icon": "♋",
     "description": "Guardiões da lua: emoção, proteção e intuição."},
    {"name": "Círculo de Leão", "slug": "leao", "category": "signo", "icon": "♌",
     "description": "Soberanos do sol: criatividade, brilho e generosidade."},
    {"name": "Círculo de Virgem", "slug": "virgem", "category": "signo", "icon": "♍",
     "description": "Alquimistas da terra: cura, serviço e perfeição."},
    {"name": "Círculo de Libra", "slug": "libra", "category": "signo", "icon": "♎",
     "description": "Artistas do equilíbrio: harmonia, beleza e justiça."},
    {"name": "Círculo de Escorpião", "slug": "escorpiao", "category": "signo", "icon": "♏",
     "description": "Místicos da transformação: profundidade, poder e renascimento."},
    {"name": "Círculo de Sagitário", "slug": "sagitario", "category": "signo", "icon": "♐",
     "description": "Exploradores do fogo: sabedoria, expansão e liberdade."},
    {"name": "Círculo de Capricórnio", "slug": "capricornio", "category": "signo", "icon": "♑",
     "description": "Mestres da montanha: disciplina, ambição e legado."},
    {"name": "Círculo de Aquário", "slug": "aquario", "category": "signo", "icon": "♒",
     "description": "Visionários do futuro: inovação, liberdade e coletivo."},
    {"name": "Círculo de Peixes", "slug": "peixes", "category": "signo", "icon": "♓",
     "description": "Místicos do oceano: compaixão, espiritualidade e arte."},
    # Temáticos
    {"name": "Tarot & Oráculos", "slug": "tarot-oraculos", "category": "pratica", "icon": "🔮",
     "description": "Compartilhe leituras, tire dúvidas e aprenda com outros tarólogos."},
    {"name": "Meditação & Rituais", "slug": "meditacao-rituais", "category": "pratica", "icon": "🧘",
     "description": "Práticas contemplativas, rituais lunares e meditações guiadas."},
    {"name": "Sonhos & Inconsciente", "slug": "sonhos-inconsciente", "category": "tema", "icon": "🌙",
     "description": "Interpretação de sonhos, trabalho de sombra e jornada interior."},
    {"name": "Manifestação & Abundância", "slug": "manifestacao-abundancia", "category": "tema", "icon": "✨",
     "description": "Lei da atração, afirmações, quadro de visão e prosperidade."},
]


def seed_community_groups():
    db = SessionLocal()
    try:
        created = 0
        for group_data in DEFAULT_GROUPS:
            existing = db.query(models.CommunityGroup).filter_by(
                slug=group_data["slug"]
            ).first()
            if not existing:
                group = models.CommunityGroup(
                    name=group_data["name"],
                    slug=group_data["slug"],
                    category=group_data["category"],
                    icon=group_data["icon"],
                    description=group_data["description"],
                    is_public=True,
                    oracle_enabled=True,
                )
                db.add(group)
                created += 1
        db.commit()
        print(f"[community_seed] {created} grupos criados ({len(DEFAULT_GROUPS) - created} já existiam)")
    finally:
        db.close()


if __name__ == "__main__":
    seed_community_groups()
