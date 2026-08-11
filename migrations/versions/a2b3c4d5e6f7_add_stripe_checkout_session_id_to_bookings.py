"""add stripe_checkout_session_id to bookings table

Revision ID: a2b3c4d5e6f7
Revises: a1b2c3d4e5f6
Create Date: 2026-08-11 17:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a2b3c4d5e6f7'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    columns = [c['name'] for c in inspector.get_columns('bookings')]
    if 'stripe_checkout_session_id' not in columns:
        with op.batch_alter_table('bookings', schema=None) as batch_op:
            batch_op.add_column(sa.Column('stripe_checkout_session_id', sa.String(length=255), nullable=True))
            batch_op.create_index(batch_op.f('ix_bookings_stripe_checkout_session_id'), ['stripe_checkout_session_id'], unique=False)


def downgrade():
    with op.batch_alter_table('bookings', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_bookings_stripe_checkout_session_id'))
        batch_op.drop_column('stripe_checkout_session_id')
