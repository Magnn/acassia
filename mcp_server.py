"""Servidor MCP stdio mínimo, apoiado exclusivamente na API pública v1."""
from __future__ import annotations

import json
import os
import sys
from sdk import MeuMisterioClient

TOOLS = [
    {"name": "get_contact", "description": "Busca um contato por ID ou telefone.", "inputSchema": {"type": "object", "properties": {"contact": {"type": "string"}}, "required": ["contact"]}},
    {"name": "upsert_contact", "description": "Cria ou atualiza um contato.", "inputSchema": {"type": "object", "properties": {"phone": {"type": "string"}, "name": {"type": "string"}, "tags": {"type": "array", "items": {"type": "string"}}}, "required": ["phone"]}},
    {"name": "send_message", "description": "Envia mensagem por um canal configurado.", "inputSchema": {"type": "object", "properties": {"recipient": {"type": "string"}, "text": {"type": "string"}, "channel": {"type": "string"}}, "required": ["recipient", "text"]}},
    {"name": "enroll_sequence", "description": "Inscreve um contato em uma sequência.", "inputSchema": {"type": "object", "properties": {"sequence_id": {"type": "integer"}, "contact_id": {"type": "integer"}, "phone": {"type": "string"}}, "required": ["sequence_id"]}},
]


def _client() -> MeuMisterioClient:
    return MeuMisterioClient(os.getenv("MM_BASE_URL", "http://localhost:5000"), os.environ["MM_API_KEY"])


def handle(message: dict) -> dict | None:
    method, request_id = message.get("method"), message.get("id")
    if method == "notifications/initialized": return None
    if method == "initialize":
        result = {"protocolVersion": "2025-03-26", "capabilities": {"tools": {}}, "serverInfo": {"name": "meu-misterio", "version": "1.0.0"}}
    elif method == "tools/list": result = {"tools": TOOLS}
    elif method == "tools/call":
        params = message.get("params") or {}; name = params.get("name"); args = params.get("arguments") or {}; client = _client()
        if name == "get_contact": value = client.get_contact(args["contact"])
        elif name == "upsert_contact": value = client.upsert_contact(args["phone"], args.get("name", ""), args.get("tags", []))
        elif name == "send_message": value = client.send_message(args["recipient"], args["text"], args.get("channel", "whatsapp"))
        elif name == "enroll_sequence": value = client.enroll_sequence(args["sequence_id"], contact_id=args.get("contact_id"), phone=args.get("phone"))
        else: return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "tool_not_found"}}
        result = {"content": [{"type": "text", "text": json.dumps(value, ensure_ascii=False)}]}
    else: return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32601, "message": "method_not_found"}}
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def main() -> None:
    for line in sys.stdin:
        try:
            response = handle(json.loads(line))
            if response is not None:
                print(json.dumps(response, ensure_ascii=False), flush=True)
        except Exception as exc:
            print(json.dumps({"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(exc)}}), flush=True)


if __name__ == "__main__": main()
