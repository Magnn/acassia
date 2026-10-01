"""Allow multiple published flow blueprints per tenant."""
from alembic import op
import sqlalchemy as sa


revision = "a8b9c0d1e2f3"
down_revision = "549551fd5210"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("flow_publish") as batch_op:
        batch_op.drop_index("ix_flow_publish_tenant_id")
        batch_op.create_index("ix_flow_publish_tenant_id", ["tenant_id"], unique=False)
        batch_op.create_unique_constraint(
            "uq_flow_publish_tenant_blueprint",
            ["tenant_id", "published_blueprint_id"],
        )


def downgrade():
    duplicates = op.get_bind().execute(
        sa.text(
            "SELECT tenant_id FROM flow_publish GROUP BY tenant_id "
            "HAVING COUNT(*) > 1 LIMIT 1"
        )
    ).first()
    if duplicates:
        raise RuntimeError("Cannot restore one-flow-per-tenant while multiple flows are published")

    with op.batch_alter_table("flow_publish") as batch_op:
        batch_op.drop_constraint("uq_flow_publish_tenant_blueprint", type_="unique")
        batch_op.drop_index("ix_flow_publish_tenant_id")
        batch_op.create_index("ix_flow_publish_tenant_id", ["tenant_id"], unique=True)
