"""Merge otimista e idempotência de metadata."""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from db.database import Base
from db.models import Lead
from reliability.lead_metadata_atomic import atomic_patch_metadata_json, atomic_update_lead_columns


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    lead = Lead(telefone="5511999999999", tenant_id="default", node_atual="static_meumisterio_b1")
    s.add(lead)
    s.commit()
    s.refresh(lead)
    yield s, lead.id
    s.close()


def test_atomic_patch_increments_version(db_session):
    db, lead_id = db_session
    ok = atomic_patch_metadata_json(
        db,
        lead_id,
        lambda old: {**old, "x": 1},
        max_retries=5,
    )
    assert ok
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    assert lead.metadata_json.get("x") == 1
    assert int(lead.metadata_version or 0) == 1


def test_atomic_patch_retry_on_conflict(db_session):
    db, lead_id = db_session
    ok1 = atomic_patch_metadata_json(
        db,
        lead_id,
        lambda old: {**old, "a": 1},
        max_retries=5,
    )
    assert ok1
    # Simula outra thread: version no DB mais alta que o objeto "stale"
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    v = int(lead.metadata_version or 0)
    db.query(Lead).filter(Lead.id == lead_id).update(
        {"metadata_json": {**(lead.metadata_json or {}), "b": 2}, "metadata_version": v + 1},
        synchronize_session=False,
    )
    db.commit()
    ok2 = atomic_patch_metadata_json(
        db,
        lead_id,
        lambda old: {**old, "c": 3},
        max_retries=5,
    )
    assert ok2
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    assert lead.metadata_json.get("c") == 3
    assert lead.metadata_json.get("b") == 2


def test_atomic_update_columns_multifield(db_session):
    db, lead_id = db_session

    def build(lead_row):
        return {
            Lead.estado_coleta: "x",
            Lead.metadata_json: {"k": 1},
        }

    ok = atomic_update_lead_columns(db, lead_id, build, max_retries=5)
    assert ok
    lead = db.query(Lead).filter(Lead.id == lead_id).first()
    assert lead.estado_coleta == "x"
    assert lead.metadata_json.get("k") == 1
    assert int(lead.metadata_version or 0) == 1
