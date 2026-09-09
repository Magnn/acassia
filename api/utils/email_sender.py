"""
api/utils/email_sender.py — Disparador de e-mails transacionais (Resend / SMTP)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Suporta:
1. Resend API (via RESEND_API_KEY)
2. SMTP padrão (via SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS)
3. Fallback inteligente quando nenhum provedor de email estiver configurado.
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import requests

logger = logging.getLogger(__name__)


def is_email_service_configured() -> bool:
    """Retorna True se houver Resend ou SMTP configurado nas variáveis de ambiente."""
    if os.getenv("RESEND_API_KEY"):
        return True
    if os.getenv("SMTP_HOST") and os.getenv("SMTP_USER") and os.getenv("SMTP_PASS"):
        return True
    return False


def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
    from_email: Optional[str] = None,
) -> bool:
    """
    Envia e-mail transacional usando o provedor disponível (Resend ou SMTP).
    Retorna True em caso de sucesso ou False se não configurado ou houver falha.
    """
    to_email = (to_email or "").strip().lower()
    if not to_email or "@" not in to_email:
        logger.warning("[email_sender] E-mail destinatário inválido: %s", to_email)
        return False

    sender = from_email or os.getenv("EMAIL_FROM") or os.getenv("SMTP_FROM") or "Acássia <nao-responda@acassia.com.br>"

    # 1. Tentativa via Resend API
    resend_key = os.getenv("RESEND_API_KEY")
    if resend_key:
        try:
            resend_sender = os.getenv("RESEND_FROM") or sender
            if "acassia.com.br" in resend_sender and not os.getenv("RESEND_DOMAIN_VERIFIED"):
                resend_sender = "Acássia <onboarding@resend.dev>"

            resp = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {resend_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "from": resend_sender,
                    "to": [to_email],
                    "subject": subject,
                    "html": html_content,
                    "text": text_content or "",
                },
                timeout=10,
            )
            if resp.status_code in (200, 201):
                logger.info("[email_sender.resend] E-mail enviado para %s (id: %s)", to_email, resp.json().get("id"))
                return True
            else:
                logger.error("[email_sender.resend] Falha Resend HTTP %d: %s", resp.status_code, resp.text)
        except Exception as exc:
            logger.exception("[email_sender.resend] Exceção ao enviar via Resend: %s", exc)

    # 2. Tentativa via SMTP padrão
    smtp_host = os.getenv("SMTP_HOST")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    if smtp_host and smtp_user and smtp_pass:
        smtp_port = int(os.getenv("SMTP_PORT", "587"))
        use_ssl = os.getenv("SMTP_USE_SSL", "false").lower() in ("true", "1")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to_email

        if text_content:
            msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        try:
            if use_ssl or smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)
            else:
                server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
                server.starttls()

            server.login(smtp_user, smtp_pass)
            server.sendmail(sender, [to_email], msg.as_string())
            server.quit()
            logger.info("[email_sender.smtp] E-mail enviado com sucesso para %s", to_email)
            return True
        except Exception as exc:
            logger.exception("[email_sender.smtp] Falha ao enviar via SMTP (%s:%s): %s", smtp_host, smtp_port, exc)

    logger.warning("[email_sender] Nenhum provedor de e-mail ativo para enviar a %s", to_email)
    return False


def send_password_reset_email(to_email: str, reset_url: str) -> bool:
    """Envia o e-mail transacional com o link seguro de recuperação de senha."""
    subject = "Recuperação de Senha — Acássia"
    html_content = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #09090b; color: #f4f4f5; margin: 0; padding: 0; }}
    .wrapper {{ max-width: 540px; margin: 40px auto; background-color: #18181b; border: 1px solid #27272a; border-radius: 16px; overflow: hidden; box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5); }}
    .header {{ padding: 32px 32px 24px; text-align: center; border-bottom: 1px solid #27272a; background: linear-gradient(180deg, rgba(99, 102, 241, 0.1) 0%, transparent 100%); }}
    .content {{ padding: 32px; }}
    .title {{ font-size: 20px; font-weight: 700; color: #ffffff; margin-bottom: 12px; }}
    .text {{ font-size: 14px; line-height: 1.6; color: #a1a1aa; margin-bottom: 24px; }}
    .btn {{ display: inline-block; padding: 12px 28px; background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: #ffffff !important; text-decoration: none; border-radius: 10px; font-size: 14px; font-weight: 600; text-align: center; }}
    .footer {{ padding: 24px 32px; border-top: 1px solid #27272a; font-size: 12px; color: #71717a; text-align: center; }}
    .raw-link {{ word-break: break-all; color: #818cf8; font-size: 12px; }}
  </style>
</head>
<body>
  <div class="wrapper">
    <div class="header">
      <div style="display:inline-block; width:44px; height:44px; line-height:44px; border-radius:12px; background:rgba(99,102,241,0.2); border:1px solid rgba(99,102,241,0.3); font-size:20px;">
        🔑
      </div>
    </div>
    <div class="content">
      <h1 class="title">Recuperação de Senha</h1>
      <p class="text">Olá,</p>
      <p class="text">Recebemos uma solicitação para redefinir a senha de acesso da sua conta na Acássia associada a este e-mail.</p>
      <div style="text-align: center; margin: 32px 0;">
        <a href="{reset_url}" class="btn" target="_blank">Redefinir Minha Senha</a>
      </div>
      <p class="text" style="font-size: 13px;">
        Este link é de uso único e expira em <strong>1 hora</strong> por motivos de segurança.<br>
        Se você não solicitou a troca de senha, ignore este e-mail com segurança.
      </p>
      <p class="text" style="font-size: 12px; color: #71717a; margin-top: 24px;">
        Se o botão acima não funcionar, copie e cole este link no seu navegador:<br>
        <span class="raw-link">{reset_url}</span>
      </p>
    </div>
    <div class="footer">
      &copy; Acássia — Plataforma de Funis & IA de Vendas
    </div>
  </div>
</body>
</html>"""
    text_content = (
        f"Recuperação de Senha — Acássia\n\n"
        f"Recebemos uma solicitação para redefinir a senha da sua conta.\n\n"
        f"Acesse o link abaixo para criar uma nova senha:\n{reset_url}\n\n"
        f"Este link é válido por 1 hora.\nSe você não solicitou, ignore esta mensagem."
    )
    return send_email(to_email=to_email, subject=subject, html_content=html_content, text_content=text_content)
