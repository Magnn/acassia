"""
api/utils/email_sender.py — Disparador de e-mails transacionais multi-provedor
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Detecta e suporta automaticamente múltiplos padrões de variáveis de ambiente:
1. Resend API (RESEND_API_KEY / RESEND_KEY / RESEND_TOKEN)
2. SendGrid API (SENDGRID_API_KEY / SENDGRID_KEY)
3. SMTP Padrão / Flask-Mail / Django / cPanel / Gmail / SendGrid SMTP / Mailgun / AWS SES:
   - Host: SMTP_HOST, SMTP_SERVER, MAIL_SERVER, EMAIL_HOST, MAIL_HOST
   - Port: SMTP_PORT, MAIL_PORT, EMAIL_PORT
   - User: SMTP_USER, SMTP_USERNAME, MAIL_USERNAME, EMAIL_HOST_USER, EMAIL_USER, GMAIL_USER
   - Pass: SMTP_PASS, SMTP_PASSWORD, MAIL_PASSWORD, EMAIL_HOST_PASSWORD, EMAIL_PASSWORD, EMAIL_PASS, GMAIL_APP_PASSWORD
   - From: EMAIL_FROM, SMTP_FROM, MAIL_FROM, MAIL_DEFAULT_SENDER, DEFAULT_FROM_EMAIL, RESEND_FROM
"""

from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


def _get_resend_key() -> Optional[str]:
    return (
        os.getenv("RESEND_API_KEY")
        or os.getenv("RESEND_KEY")
        or os.getenv("RESEND_TOKEN")
        or os.getenv("RESEND_SECRET")
    )


def _get_sendgrid_key() -> Optional[str]:
    return (
        os.getenv("SENDGRID_API_KEY")
        or os.getenv("SENDGRID_KEY")
    )


def _get_smtp_config() -> Tuple[Optional[str], int, Optional[str], Optional[str], bool, bool]:
    """Retorna (host, port, user, password, use_tls, use_ssl)."""
    # Host
    host = (
        os.getenv("SMTP_HOST")
        or os.getenv("SMTP_SERVER")
        or os.getenv("MAIL_SERVER")
        or os.getenv("EMAIL_HOST")
        or os.getenv("MAIL_HOST")
    )

    # Gmail shortcut se não tiver host explícito
    gmail_user = os.getenv("GMAIL_USER")
    gmail_pass = os.getenv("GMAIL_APP_PASSWORD") or os.getenv("GMAIL_PASSWORD")
    if not host and gmail_user and gmail_pass:
        host = "smtp.gmail.com"

    # User
    user = (
        os.getenv("SMTP_USER")
        or os.getenv("SMTP_USERNAME")
        or os.getenv("MAIL_USERNAME")
        or os.getenv("EMAIL_HOST_USER")
        or os.getenv("EMAIL_USER")
        or gmail_user
    )

    # Password
    password = (
        os.getenv("SMTP_PASS")
        or os.getenv("SMTP_PASSWORD")
        or os.getenv("MAIL_PASSWORD")
        or os.getenv("EMAIL_HOST_PASSWORD")
        or os.getenv("EMAIL_PASSWORD")
        or os.getenv("EMAIL_PASS")
        or gmail_pass
    )

    # Port
    port_str = os.getenv("SMTP_PORT") or os.getenv("MAIL_PORT") or os.getenv("EMAIL_PORT") or ""
    if port_str.isdigit():
        port = int(port_str)
    elif host == "smtp.gmail.com":
        port = 587
    else:
        port = 587

    # SSL / TLS
    ssl_env = (os.getenv("SMTP_USE_SSL") or os.getenv("MAIL_USE_SSL") or os.getenv("EMAIL_USE_SSL") or "").lower()
    tls_env = (os.getenv("SMTP_USE_TLS") or os.getenv("MAIL_USE_TLS") or os.getenv("EMAIL_USE_TLS") or "").lower()

    use_ssl = ssl_env in ("true", "1", "yes") or port == 465
    use_tls = tls_env in ("true", "1", "yes") or (not use_ssl and port == 587)

    return host, port, user, password, use_tls, use_ssl


def _get_default_sender() -> str:
    return (
        os.getenv("EMAIL_FROM")
        or os.getenv("SMTP_FROM")
        or os.getenv("MAIL_FROM")
        or os.getenv("MAIL_DEFAULT_SENDER")
        or os.getenv("DEFAULT_FROM_EMAIL")
        or os.getenv("RESEND_FROM")
        or os.getenv("RESEND_FROM_EMAIL")
        or "Acássia <nao-responda@acassia.com.br>"
    )


def is_email_service_configured() -> bool:
    """Verifica se há qualquer provedor de e-mail transacional configurado."""
    if _get_resend_key():
        return True
    if _get_sendgrid_key():
        return True
    host, _, user, password, _, _ = _get_smtp_config()
    if host and user and password:
        return True
    return False


def get_email_diagnostic_info() -> Dict[str, Any]:
    """Retorna o status dos provedores para diagnóstico e auditoria de deploy."""
    resend_k = _get_resend_key()
    sendgrid_k = _get_sendgrid_key()
    host, port, user, _, use_tls, use_ssl = _get_smtp_config()

    active_provider = "none"
    if resend_k:
        active_provider = "resend"
    elif sendgrid_k:
        active_provider = "sendgrid"
    elif host and user:
        active_provider = "smtp"

    return {
        "configured": is_email_service_configured(),
        "active_provider": active_provider,
        "resend_detected": bool(resend_k),
        "sendgrid_detected": bool(sendgrid_k),
        "smtp_host": host or None,
        "smtp_port": port,
        "smtp_user": user or None,
        "smtp_tls": use_tls,
        "smtp_ssl": use_ssl,
        "default_sender": _get_default_sender(),
    }


def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
    from_email: Optional[str] = None,
) -> bool:
    """
    Envia e-mail transacional usando o provedor disponível (Resend, SendGrid ou SMTP).
    """
    to_email = (to_email or "").strip().lower()
    if not to_email or "@" not in to_email:
        logger.warning("[email_sender] E-mail destinatário inválido: %s", to_email)
        return False

    sender = from_email or _get_default_sender()

    # 1. Provedor Resend
    resend_key = _get_resend_key()
    if resend_key:
        try:
            resend_sender = sender
            # Domínio sandbox default do Resend caso acassia.com.br não tenha DKIM no Resend
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
                logger.info("[email_sender.resend] E-mail enviado com sucesso para %s (id=%s)", to_email, resp.json().get("id"))
                return True
            else:
                logger.error("[email_sender.resend] Resend retornou erro HTTP %d: %s", resp.status_code, resp.text)
        except Exception as exc:
            logger.exception("[email_sender.resend] Exceção na chamada Resend: %s", exc)

    # 2. Provedor SendGrid
    sendgrid_key = _get_sendgrid_key()
    if sendgrid_key:
        try:
            resp = requests.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={
                    "Authorization": f"Bearer {sendgrid_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "personalizations": [{"to": [{"email": to_email}]}],
                    "from": {"email": sender.split("<")[-1].replace(">", "").strip(), "name": "Acássia"},
                    "subject": subject,
                    "content": [
                        {"type": "text/html", "value": html_content}
                    ],
                },
                timeout=10,
            )
            if resp.status_code in (200, 202):
                logger.info("[email_sender.sendgrid] E-mail enviado com sucesso para %s", to_email)
                return True
            else:
                logger.error("[email_sender.sendgrid] SendGrid retornou erro HTTP %d: %s", resp.status_code, resp.text)
        except Exception as exc:
            logger.exception("[email_sender.sendgrid] Exceção na chamada SendGrid: %s", exc)

    # 3. Provedor SMTP Genérico / Gmail / AWS SES / cPanel
    host, port, user, password, use_tls, use_ssl = _get_smtp_config()
    if host and user and password:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = to_email

        if text_content:
            msg.attach(MIMEText(text_content, "plain", "utf-8"))
        msg.attach(MIMEText(html_content, "html", "utf-8"))

        try:
            if use_ssl or port == 465:
                server = smtplib.SMTP_SSL(host, port, timeout=15)
            else:
                server = smtplib.SMTP(host, port, timeout=15)
                if use_tls:
                    server.starttls()

            server.login(user, password)
            server.sendmail(sender, [to_email], msg.as_string())
            server.quit()
            logger.info("[email_sender.smtp] E-mail enviado com sucesso via %s:%s para %s", host, port, to_email)
            return True
        except Exception as exc:
            logger.exception("[email_sender.smtp] Falha ao enviar via SMTP (%s:%s): %s", host, port, exc)

    logger.warning("[email_sender] Nenhum provedor de e-mail conseguiu entregar para %s", to_email)
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
