"""
scripts/sync_chatbotx_audit.py — Monitor de Atualizações Contínuas do ChatbotX
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Este script verifica os últimos commits e arquivos modificados no repositório
https://github.com/ChatbotXIO/ChatbotX para alertar sobre novas features,
mudanças de arquitetura ou correções adicionadas pela equipe do ChatbotX.
"""

import urllib.request
import json
import os
import sys
from datetime import datetime

REPO_OWNER = "ChatbotXIO"
REPO_NAME = "ChatbotX"
API_COMMITS_URL = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/commits?per_page=15"

def fetch_latest_updates():
    req = urllib.request.Request(API_COMMITS_URL, headers={"User-Agent": "Acassia-Audit-Engine"})
    try:
        with urllib.request.urlopen(req) as resp:
            commits = json.loads(resp.read().decode("utf-8"))
        
        print(f"=== ÚLTIMOS COMMITS DETECTADOS NO CHATBOTX ({datetime.now().strftime('%d/%m/%Y %H:%M')}) ===")
        for c in commits:
            sha = c["sha"][:7]
            author = c["commit"]["author"]["name"]
            date_str = c["commit"]["author"]["date"]
            msg = c["commit"]["message"].split("\n")[0]
            print(f"[{sha}] {date_str[:10]} | {author}: {msg}")
            
    except Exception as exc:
        print(f"Erro ao consultar API do GitHub: {exc}")

if __name__ == "__main__":
    fetch_latest_updates()
