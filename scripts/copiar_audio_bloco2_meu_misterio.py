"""
Copia o PTT do Bloco 2 para assets/funil_estatico_meu_misterio/audio/bloco2_interpretacao_ptt.ogg

Uso:
  python scripts/copiar_audio_bloco2_meu_misterio.py "C:\\caminho\\para\\ficheiro.ogg"

Se não passar caminho, tenta %USERPROFILE%\\Downloads e o primeiro *.ogg com "Ptt" ou "ptt" no nome.
"""
from __future__ import annotations

import os
import shutil
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_DEST = os.path.join(
    _ROOT, "assets", "funil_estatico_meu_misterio", "audio", "bloco2_interpretacao_ptt.ogg"
)


def main() -> int:
    src = (sys.argv[1] if len(sys.argv) > 1 else "").strip()
    if not src:
        dl = os.path.join(os.environ.get("USERPROFILE", ""), "Downloads")
        if os.path.isdir(dl):
            for name in sorted(os.listdir(dl), reverse=True):
                low = name.lower()
                if not low.endswith(".ogg"):
                    continue
                if "ptt" in low or "whatsapp" in low:
                    cand = os.path.join(dl, name)
                    if os.path.isfile(cand):
                        src = cand
                        print(f"Usando: {src}")
                        break
    if not src or not os.path.isfile(src):
        print("Ficheiro de origem não encontrado. Passe o caminho completo do .ogg como argumento.")
        return 1
    os.makedirs(os.path.dirname(_DEST), exist_ok=True)
    shutil.copy2(src, _DEST)
    print(f"Copiado para: {_DEST}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
