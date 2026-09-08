"""tests/test_social_automations_execution.py — Testes da execução de Comment-to-DM."""
from unittest.mock import patch, MagicMock
from db.database import SessionLocal
from db import models
from api.public.social_automations import (
    process_social_comment,
    reply_to_instagram_comment,
    send_instagram_private_reply,
    send_instagram_direct_message,
    _put_variable,
    _put_secret,
)


def test_reply_to_instagram_comment_success():
    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        ok = reply_to_instagram_comment("c_123", "Obrigado pelo comentário!", "token_abc")
        assert ok is True
        mock_post.assert_called_once()


def test_send_instagram_private_reply_success():
    with patch("requests.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        ok = send_instagram_private_reply("c_123", "Aqui está o link prometido", "token_abc")
        assert ok is True
        mock_post.assert_called_once()


def test_send_instagram_direct_message_uses_recipient_id():
    with patch("requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        assert send_instagram_direct_message("ig_user_1", "Olá", "token_abc") is True
        assert mock_post.call_args.kwargs["json"]["recipient"] == {"id": "ig_user_1"}


def test_process_social_comment_matching_rule():
    db = SessionLocal()
    tenant_id = "test_social_tenant"
    try:
        # Configurar regras e secret
        _put_variable(db, tenant_id, "social.comment_rules", [
            {
                "id": "rule_1",
                "keyword": "EU QUERO",
                "reply_comment": "Enviado no direct! 🔮",
                "send_dm": "Aqui está seu cupom exclusivo: QUERO10",
                "active": True,
            }
        ])
        _put_secret(db, tenant_id, "meta_social.access_token", "test_ig_token")
        db.commit()

        comment_data = {
            "id": "comment_999",
            "text": "Eu quero muito saber meu signo ascendente!",
            "from": {"id": "user_888", "username": "maria_astral"},
        }

        with patch("api.public.social_automations.reply_to_instagram_comment") as mock_reply, \
             patch("api.public.social_automations.send_instagram_private_reply") as mock_dm:
            mock_reply.return_value = True
            mock_dm.return_value = True

            matched = process_social_comment(tenant_id, comment_data, db)
            assert matched == 1
            mock_reply.assert_called_once_with("comment_999", "Enviado no direct! 🔮", "test_ig_token")
            mock_dm.assert_called_once_with("comment_999", "Aqui está seu cupom exclusivo: QUERO10", "test_ig_token")

        # Verificar se Lead foi criado com a tag comment_to_dm
        lead = db.query(models.Lead).filter_by(tenant_id=tenant_id, telefone="user_888").first()
        assert lead is not None
        assert "comment_to_dm" in (lead.tags or [])
        assert "instagram" in (lead.tags or [])

    finally:
        db.close()


def test_process_social_comment_unmatching_rule():
    db = SessionLocal()
    tenant_id = "test_social_tenant_unmatch"
    try:
        _put_variable(db, tenant_id, "social.comment_rules", [
            {
                "id": "rule_1",
                "keyword": "PROMOÇÃO",
                "reply_comment": "Enviado!",
                "send_dm": "Link",
                "active": True,
            }
        ])
        db.commit()

        comment_data = {
            "id": "comment_1000",
            "text": "Muito legal o post de hoje!",
            "from": {"id": "user_777", "username": "joao"},
        }

        with patch("api.public.social_automations.reply_to_instagram_comment") as mock_reply, \
             patch("api.public.social_automations.send_instagram_private_reply") as mock_dm:
            matched = process_social_comment(tenant_id, comment_data, db)
            assert matched == 0
            mock_reply.assert_not_called()
            mock_dm.assert_not_called()
    finally:
        db.close()
