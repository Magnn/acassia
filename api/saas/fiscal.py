"""
api/saas/fiscal.py
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Módulo de Integração Fiscal SaaS (NFe / NFSe / NFCe)

Emite e rastreia notas fiscais usando uma API terceirizada
(ex: Nuvem Fiscal, Focus NFe) abstraindo a complexidade do SOAP/SEFAZ.
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy.orm import Session
from datetime import datetime
import traceback
import requests
import os

from db.database import SessionLocal, set_tenant_rls
from db.models import NotaFiscal, Lead

fiscal_bp = Blueprint("saas_fiscal_bp", __name__, url_prefix="/api/saas/fiscal")

# ─── Configurações Mockadas (Adaptar para a API Real escolhida) ───
NUVEM_FISCAL_API_URL = os.getenv("NUVEM_FISCAL_API_URL", "https://api.nuvemfiscal.com.br/v1")
NUVEM_FISCAL_CLIENT_ID = os.getenv("NUVEM_FISCAL_CLIENT_ID", "")
NUVEM_FISCAL_CLIENT_SECRET = os.getenv("NUVEM_FISCAL_CLIENT_SECRET", "")

def emitir_nota_na_api(tenant_id: str, dados_nota: dict) -> dict:
    """
    Função mock que simula a chamada à API da Nuvem Fiscal ou Focus NFe.
    Num cenário real, aqui seria montado o payload JSON e feito o requests.post.
    """
    # Exemplo real:
    # headers = {"Authorization": f"Bearer {obter_token_oauth()}"}
    # resp = requests.post(f"{NUVEM_FISCAL_API_URL}/nfse", json=dados_nota, headers=headers)
    # return resp.json()
    
    # Mock return
    import uuid
    import random
    
    return {
        "id": f"nf_{uuid.uuid4().hex[:12]}",
        "status": "autorizada",
        "ambiente": dados_nota.get("ambiente", "homologacao"),
        "numero": random.randint(1000, 9999),
        "serie": "1",
        "chave_acesso": "".join([str(random.randint(0, 9)) for _ in range(44)]),
        "pdf_url": "https://api.nuvemfiscal.com.br/v1/nfse/pdf/mock_123",
        "xml_url": "https://api.nuvemfiscal.com.br/v1/nfse/xml/mock_123",
    }


def emitir_nota_automatica_webhook(tenant_id: str, lead_id: int, valor: float, cpf_cnpj: str, nome_cliente: str, descricao: str) -> bool:
    """Helper para emissão assíncrona automática via webhooks de faturamento (Cakto)."""
    db: Session = SessionLocal()
    set_tenant_rls(db, tenant_id)
    try:
        dados_api = {
            "ambiente": "producao",
            "tipo": "NFSe",
            "valor_total": float(valor),
            "tomador": {
                "cpf_cnpj": cpf_cnpj,
                "nome": nome_cliente
            },
            "servico": {
                "descricao": descricao
            }
        }
        
        retorno_api = emitir_nota_na_api(tenant_id, dados_api)
        
        nova_nota = NotaFiscal(
            tenant_id=tenant_id,
            lead_id=lead_id,
            ambiente=retorno_api.get("ambiente", "homologacao"),
            tipo_documento="NFSe",
            numero=retorno_api.get("numero"),
            serie=retorno_api.get("serie"),
            chave_acesso=retorno_api.get("chave_acesso"),
            valor_total=float(valor),
            cpf_cnpj=cpf_cnpj,
            nome_cliente=nome_cliente,
            descricao_servico=descricao,
            status=retorno_api.get("status", "processando"),
            api_reference_id=retorno_api.get("id"),
            url_pdf=retorno_api.get("pdf_url"),
            url_xml=retorno_api.get("xml_url")
        )
        db.add(nova_nota)
        db.commit()
        return True
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Erro ao emitir NF automática: {e}")
        db.rollback()
        return False
    finally:
        db.close()


@fiscal_bp.route("/emitir", methods=["POST"])
@login_required
def emitir_nota():
    """
    Emite uma nova Nota Fiscal (NFSe / NFe).
    
    Corpo (JSON):
      - lead_id (int): Opcional
      - valor (float): Valor da nota
      - documento (str): CPF/CNPJ
      - nome (str): Nome do cliente
      - descricao (str): Descrição do serviço/produto
      - tipo (str): "NFSe", "NFe" ou "NFCe"
    """
    tenant_id = current_user.tenant_id
    payload = request.get_json() or {}

    valor = payload.get("valor")
    cpf_cnpj = payload.get("documento")
    nome_cliente = payload.get("nome")
    descricao = payload.get("descricao", "Serviço Prestado")
    tipo = payload.get("tipo", "NFSe")
    lead_id = payload.get("lead_id")

    if not valor or not cpf_cnpj or not nome_cliente:
        return jsonify({"error": "valor, documento e nome são obrigatórios"}), 400

    db: Session = SessionLocal()
    set_tenant_rls(db, tenant_id)
    try:
        # Montar payload para a API externa
        dados_api = {
            "ambiente": "producao", # ou homologacao
            "tipo": tipo,
            "valor_total": float(valor),
            "tomador": {
                "cpf_cnpj": cpf_cnpj,
                "nome": nome_cliente
            },
            "servico": {
                "descricao": descricao
            }
        }
        
        # Chamar a API terceira para emissão
        retorno_api = emitir_nota_na_api(tenant_id, dados_api)
        
        # Registrar no banco local
        nova_nota = NotaFiscal(
            tenant_id=tenant_id,
            lead_id=lead_id,
            ambiente=retorno_api.get("ambiente", "homologacao"),
            tipo_documento=tipo,
            numero=retorno_api.get("numero"),
            serie=retorno_api.get("serie"),
            chave_acesso=retorno_api.get("chave_acesso"),
            valor_total=float(valor),
            cpf_cnpj=cpf_cnpj,
            nome_cliente=nome_cliente,
            descricao_servico=descricao,
            status=retorno_api.get("status", "processando"),
            api_reference_id=retorno_api.get("id"),
            url_pdf=retorno_api.get("pdf_url"),
            url_xml=retorno_api.get("xml_url")
        )
        db.add(nova_nota)
        db.commit()
        db.refresh(nova_nota)

        return jsonify({
            "ok": True,
            "message": "Nota Fiscal registrada para emissão",
            "nota": {
                "id": nova_nota.id,
                "status": nova_nota.status,
                "chave_acesso": nova_nota.chave_acesso,
                "numero": nova_nota.numero,
                "pdf_url": nova_nota.url_pdf
            }
        }), 201

    except Exception as e:
        db.rollback()
        return jsonify({"error": str(e), "trace": traceback.format_exc()}), 500
    finally:
        db.close()


@fiscal_bp.route("/notas", methods=["GET"])
@login_required
def listar_notas():
    """Lista as notas fiscais emitidas pelo tenant."""
    tenant_id = current_user.tenant_id
    limit = int(request.args.get("limit", 50))
    offset = int(request.args.get("offset", 0))

    db: Session = SessionLocal()
    set_tenant_rls(db, tenant_id)
    try:
        query = db.query(NotaFiscal).filter(NotaFiscal.tenant_id == tenant_id)
        
        # Filtros opcionais
        status = request.args.get("status")
        if status:
            query = query.filter(NotaFiscal.status == status)
            
        lead_id = request.args.get("lead_id")
        if lead_id:
            query = query.filter(NotaFiscal.lead_id == int(lead_id))

        total = query.count()
        notas = query.order_by(NotaFiscal.created_at.desc()).offset(offset).limit(limit).all()

        data = []
        for n in notas:
            data.append({
                "id": n.id,
                "tipo": n.tipo_documento,
                "numero": n.numero,
                "chave_acesso": n.chave_acesso,
                "valor_total": n.valor_total,
                "nome_cliente": n.nome_cliente,
                "cpf_cnpj": n.cpf_cnpj,
                "status": n.status,
                "url_pdf": n.url_pdf,
                "created_at": n.created_at.isoformat() if n.created_at else None
            })

        return jsonify({
            "ok": True,
            "total": total,
            "limit": limit,
            "offset": offset,
            "data": data
        }), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()
