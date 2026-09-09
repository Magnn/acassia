"""enforce one booking per tenant and time

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
"""
from alembic import op
from sqlalchemy.engine.reflection import Inspector


revision = "d0e1f2a3b4c5"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def _unique_names(inspector, table):
    return {item.get("name") for item in inspector.get_unique_constraints(table)}


def upgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    tables = set(inspector.get_table_names())
    if "expert_schedule_slots" in tables and "uq_expert_slot_tenant_time" not in _unique_names(inspector, "expert_schedule_slots"):
        with op.batch_alter_table("expert_schedule_slots") as batch:
            batch.create_unique_constraint("uq_expert_slot_tenant_time", ["tenant_id", "slot_time"])
    inspector = Inspector.from_engine(bind)
    if "appointments" in tables and "uq_appointment_tenant_time" not in _unique_names(inspector, "appointments"):
        with op.batch_alter_table("appointments") as batch:
            batch.create_unique_constraint("uq_appointment_tenant_time", ["tenant_id", "scheduled_at"])


def downgrade():
    bind = op.get_bind()
    inspector = Inspector.from_engine(bind)
    tables = set(inspector.get_table_names())
    if "appointments" in tables and "uq_appointment_tenant_time" in _unique_names(inspector, "appointments"):
        with op.batch_alter_table("appointments") as batch:
            batch.drop_constraint("uq_appointment_tenant_time", type_="unique")
    inspector = Inspector.from_engine(bind)
    if "expert_schedule_slots" in tables and "uq_expert_slot_tenant_time" in _unique_names(inspector, "expert_schedule_slots"):
        with op.batch_alter_table("expert_schedule_slots") as batch:
            batch.drop_constraint("uq_expert_slot_tenant_time", type_="unique")
