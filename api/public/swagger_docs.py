"""
api/public/swagger_docs.py — Documentação Interativa da API (OpenAPI 3.0 / Swagger UI)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Disponibiliza Swagger UI interativo em /api/docs para desenvolvedores e integrações externas.
"""

from __future__ import annotations

from flask import Blueprint, jsonify, render_template_string

swagger_bp = Blueprint("swagger_docs", __name__, url_prefix="/api")

SWAGGER_UI_HTML = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <title>Acássia SaaS — API Documentation</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui.css" />
  <style>
    body { margin: 0; background: #0f1117; color: #fff; }
    .swagger-ui .topbar { display: none; }
    .swagger-ui { filter: invert(88%) hue-rotate(180deg); }
    .swagger-ui .highlight-code { filter: invert(100%) hue-rotate(180deg); }
  </style>
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5.11.0/swagger-ui-bundle.js"></script>
  <script>
    window.onload = () => {
      window.ui = SwaggerUIBundle({
        url: '/api/openapi.json',
        dom_id: '#swagger-ui',
        deepLinking: true,
        presets: [
          SwaggerUIBundle.presets.apis,
          SwaggerUIBundle.SwaggerUIStandalonePreset
        ],
        layout: "BaseLayout"
      });
    };
  </script>
</body>
</html>
"""

OPENAPI_SPEC = {
    "openapi": "3.0.3",
    "info": {
        "title": "Acássia SaaS — API Oficial",
        "description": "API REST para automação de funis, mensagens WhatsApp, Webchat, CRM e atendimento humano.",
        "version": "8.8.0",
    },
    "servers": [
        {"url": "/", "description": "Servidor Atual"}
    ],
    "paths": {
        "/api/public/webchat/init": {
            "post": {
                "summary": "Inicializa sessão do visitante no Webchat",
                "tags": ["Webchat"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "tenant_id": {"type": "string", "example": "default"},
                                    "session_id": {"type": "string", "example": "web_abc123"},
                                    "name": {"type": "string", "example": "Visitante"},
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {"description": "Sessão inicializada"}
                }
            }
        },
        "/api/public/webchat/message": {
            "post": {
                "summary": "Envia mensagem pelo Webchat e recebe resposta da IA/motor",
                "tags": ["Webchat"],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["session_id", "text"],
                                "properties": {
                                    "tenant_id": {"type": "string", "example": "default"},
                                    "session_id": {"type": "string", "example": "web_abc123"},
                                    "text": {"type": "string", "example": "Olá, como funciona?"}
                                }
                            }
                        }
                    }
                },
                "responses": {
                    "200": {"description": "Resposta do motor conversacional"}
                }
            }
        },
        "/saas/devices/": {
            "get": {
                "summary": "Lista dispositivos WhatsApp cadastrados no tenant",
                "tags": ["WhatsApp Multi-Device"],
                "responses": {"200": {"description": "Lista de dispositivos"}}
            },
            "post": {
                "summary": "Cadastra novo dispositivo WhatsApp (Meta Cloud ou Evolution)",
                "tags": ["WhatsApp Multi-Device"],
                "responses": {"201": {"description": "Dispositivo criado"}}
            }
        },
        "/saas/wa/embedded-signup/config": {
            "get": {
                "summary": "Verifica se Meta Embedded Signup está configurado no servidor",
                "tags": ["WhatsApp Multi-Device"],
                "responses": {"200": {"description": "Configuração da Meta"}}
            }
        },
        "/saas/wa/embedded-signup/exchange": {
            "post": {
                "summary": "Troca o código OAuth da Meta por token permanente e registra dispositivo",
                "tags": ["WhatsApp Multi-Device"],
                "responses": {"200": {"description": "WhatsApp conectado com sucesso"}}
            }
        },
        "/saas/inbox/data": {
            "get": {
                "summary": "Lista de conversas do Inbox ordenadas por urgência",
                "tags": ["Inbox & Atendimento"],
                "responses": {"200": {"description": "Lista de leads do Inbox"}}
            }
        },
        "/saas/inbox/tags": {
            "get": {
                "summary": "Retorna lista de todas as tags usadas no tenant",
                "tags": ["Inbox & Atendimento"],
                "responses": {"200": {"description": "Lista de tags"}}
            }
        },
        "/saas/inbox/{lead_id}/tags": {
            "post": {
                "summary": "Adiciona tag a um lead",
                "tags": ["Inbox & Atendimento"],
                "parameters": [{"name": "lead_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                "responses": {"200": {"description": "Tag adicionada"}}
            }
        },
        "/saas/inbox/{lead_id}/takeover/data": {
            "post": {
                "summary": "Pausa ou retoma o robô (Human Takeover)",
                "tags": ["Inbox & Atendimento"],
                "parameters": [{"name": "lead_id", "in": "path", "required": True, "schema": {"type": "integer"}}],
                "responses": {"200": {"description": "Estado do bot alterado"}}
            }
        },
        "/saas/broadcast/": {
            "get": {
                "summary": "Lista campanhas de broadcast",
                "tags": ["Broadcast"],
                "responses": {"200": {"description": "Campanhas"}}
            },
            "post": {
                "summary": "Cria campanha de broadcast (imediata ou agendada)",
                "tags": ["Broadcast"],
                "responses": {"201": {"description": "Campanha criada"}}
            }
        }
    }
}


@swagger_bp.route("/docs", methods=["GET"])
def serve_docs():
    """Interface gráfica interativa Swagger UI."""
    return render_template_string(SWAGGER_UI_HTML)


@swagger_bp.route("/openapi.json", methods=["GET"])
def serve_openapi_spec():
    """Especificação OpenAPI 3.0 em JSON."""
    return jsonify(OPENAPI_SPEC)
