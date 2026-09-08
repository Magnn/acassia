import pytest
from datetime import datetime, timezone
from db.database import SessionLocal
from db.models import Sequence, SequenceStep, Lead, ContactOnSequence
from api.saas.sequences import check_and_enroll_by_tags

@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_auto_enroll_matching_tag(db_session):
    tenant_id = "test_tenant"
    
    # Setup Sequence and Step
    seq = Sequence(
        tenant_id=tenant_id,
        name="Test Auto Enroll",
        active=True,
        trigger_tag="vip"
    )
    db_session.add(seq)
    db_session.commit()
    db_session.refresh(seq)

    step = SequenceStep(
        sequence_id=seq.id,
        tenant_id=tenant_id,
        order=0,
        delay_days=0,
        is_active=True
    )
    db_session.add(step)
    
    # Setup Lead
    lead = Lead(
        tenant_id=tenant_id,
        telefone="11999999999",
        nome="Test Lead",
        tags=["vip"]
    )
    db_session.add(lead)
    db_session.commit()
    db_session.refresh(lead)

    # Call check_and_enroll_by_tags
    enrolled = check_and_enroll_by_tags(tenant_id, lead.id, ["vip"])
    assert enrolled == 1

    # Verify Enrollment
    enrollment = db_session.query(ContactOnSequence).filter_by(
        sequence_id=seq.id, lead_id=lead.id
    ).first()
    assert enrollment is not None
    assert enrollment.status == "active"
    assert enrollment.current_step == 0
    assert enrollment.tenant_id == tenant_id

    # Cleanup
    db_session.delete(enrollment)
    db_session.delete(lead)
    db_session.delete(step)
    db_session.delete(seq)
    db_session.commit()

def test_auto_enroll_unmatching_tag(db_session):
    tenant_id = "test_tenant"
    
    # Setup Sequence
    seq = Sequence(
        tenant_id=tenant_id,
        name="Test No Auto Enroll",
        active=True,
        trigger_tag="vip"
    )
    db_session.add(seq)
    db_session.commit()
    db_session.refresh(seq)

    step = SequenceStep(
        sequence_id=seq.id,
        tenant_id=tenant_id,
        order=0,
        delay_days=0,
        is_active=True
    )
    db_session.add(step)

    # Setup Lead
    lead = Lead(
        tenant_id=tenant_id,
        telefone="11999999998",
        nome="Test Lead 2",
        tags=["normal"]
    )
    db_session.add(lead)
    db_session.commit()
    db_session.refresh(lead)

    # Call check_and_enroll_by_tags with unmatching tag
    enrolled = check_and_enroll_by_tags(tenant_id, lead.id, ["normal"])
    assert enrolled == 0

    # Verify No Enrollment
    enrollment = db_session.query(ContactOnSequence).filter_by(
        sequence_id=seq.id, lead_id=lead.id
    ).first()
    assert enrollment is None

    # Cleanup
    db_session.delete(lead)
    db_session.delete(step)
    db_session.delete(seq)
    db_session.commit()
