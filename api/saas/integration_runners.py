import logging
import requests
import json
from typing import Dict, Any

logger = logging.getLogger(__name__)


def _lead_value(flow_vars: Dict[str, Any], field: str, default: str = "") -> str:
    """Lê tanto o contexto plano do builder quanto o formato legado aninhado."""
    for key in (f"lead.{field}", field):
        value = flow_vars.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    lead_data = flow_vars.get("lead")
    if isinstance(lead_data, dict):
        value = lead_data.get(field)
        if value is not None and str(value).strip():
            return str(value).strip()
    return default

def execute_integration(service: str, action: str, cfg: Dict[str, Any], vault_data: Dict[str, Any], flow_vars: Dict[str, Any]) -> str:
    """Routes the execution to the correct service handler."""
    
    if service == "google_sheets":
        return _execute_google_sheets(action, cfg, vault_data, flow_vars)
    elif service == "activecampaign":
        return _execute_activecampaign(action, cfg, vault_data, flow_vars)
    elif service == "cakto":
        return _execute_cakto(action, cfg, vault_data, flow_vars)
    else:
        raise ValueError(f"Serviço de integração não suportado: {service}")

def _execute_google_sheets(action: str, cfg: Dict[str, Any], vault_data: Dict[str, Any], flow_vars: Dict[str, Any]) -> str:
    if action == "append_row":
        # Usually requires an OAuth access token in vault_data
        token = vault_data.get("access_token")
        if not token:
            raise ValueError("Credencial inválida: access_token ausente para o Google Sheets.")
            
        spreadsheet_id = cfg.get("spreadsheet_id")
        sheet_name = cfg.get("sheet_name") or "Página1"
        payload_raw = cfg.get("payload")
        
        # Payload can be ["nome", "telefone"] or a dict. Sheets API v4 requires an array of arrays
        try:
            values = json.loads(payload_raw) if payload_raw else []
            if not isinstance(values, list):
                values = [str(v) for v in values.values()] # Fallback if dict
        except Exception:
            values = [payload_raw] # Just push as a single string if not JSON

        url = f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}/values/{sheet_name}:append?valueInputOption=USER_ENTERED"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        data = {
            "values": [values]
        }
        
        r = requests.post(url, headers=headers, json=data, timeout=10)
        r.raise_for_status()
        return f"Linha adicionada à planilha: {r.json()}"
        
    raise ValueError(f"Ação {action} não suportada para Google Sheets")

def _execute_activecampaign(action: str, cfg: Dict[str, Any], vault_data: Dict[str, Any], flow_vars: Dict[str, Any]) -> str:
    # Requires base_url and api_key in vault_data
    base_url = vault_data.get("base_url", "").rstrip("/")
    api_key = vault_data.get("api_key", "")
    
    if not base_url or not api_key:
        raise ValueError("Credencial inválida: base_url e api_key são necessários para o ActiveCampaign.")
        
    headers = {
        "Api-Token": api_key,
        "Content-Type": "application/json"
    }

    email = _lead_value(flow_vars, "email")
    if not email:
        raise ValueError("O contato precisa ter e-mail para sincronizar com o ActiveCampaign.")
    phone = _lead_value(flow_vars, "telefone")
    name = _lead_value(flow_vars, "nome", "Lead sem nome")

    contact_data = {"contact": {"email": email, "firstName": name, "phone": phone}}
    contact_response = requests.post(
        f"{base_url}/api/3/contact/sync",
        headers=headers,
        json=contact_data,
        timeout=10,
    )
    contact_response.raise_for_status()
    contact_id = contact_response.json().get("contact", {}).get("id")
    if not contact_id:
        raise ValueError("ActiveCampaign não retornou o ID do contato.")

    if action == "create_contact":
        list_id = cfg.get("list_id")
        if list_id:
            list_response = requests.post(
                f"{base_url}/api/3/contactLists",
                headers=headers,
                json={"contactList": {"list": list_id, "contact": contact_id, "status": 1}},
                timeout=10,
            )
            list_response.raise_for_status()
        return f"Contato atualizado no ActiveCampaign. ID: {contact_id}"

    if action == "add_tag":
        tag_id = cfg.get("tag_id")
        if not tag_id:
            raise ValueError("O ID da tag é obrigatório para adicionar uma tag no ActiveCampaign.")
        tag_response = requests.post(
            f"{base_url}/api/3/contactTags",
            headers=headers,
            json={"contactTag": {"contact": contact_id, "tag": tag_id}},
            timeout=10,
        )
        tag_response.raise_for_status()
        return f"Tag {tag_id} adicionada ao contato {contact_id} no ActiveCampaign."

    raise ValueError(f"Ação {action} não suportada para ActiveCampaign")

def _execute_cakto(action: str, cfg: Dict[str, Any], vault_data: Dict[str, Any], flow_vars: Dict[str, Any]) -> str:
    # Requires token in vault_data
    token = vault_data.get("token")
    if not token:
        raise ValueError("Credencial inválida: token ausente para o Cakto.")
        
    if action == "create_checkout":
        product_id = cfg.get("product_id")
        # In a real scenario, this would call the Cakto API to generate a unique checkout link
        # For demonstration of the integration node architecture, we return a mock success
        return f"https://pay.cakto.com.br/checkout/{product_id}?ref={_lead_value(flow_vars, 'id')}"
        
    raise ValueError(f"Ação {action} não suportada para Cakto")
