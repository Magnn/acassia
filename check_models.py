import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("--- LISTA DE MODELOS DISPONÍVEIS PARA SUA CHAVE ---")
try:
    for model in client.models.list():
        print(f"Nome: {model.name} | Versão: {model.version}")
except Exception as e:
    print(f"Erro ao listar: {e}")