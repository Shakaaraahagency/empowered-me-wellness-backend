"""add expires_at to bookings table

Revision ID: b3c4d5e6f7g8
Revises: fa645fcd2257
Create Date: 2026-08-25 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'b3c4d5e6f7g8'
down_revision = 'fa645fcd2257'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    columns = [c['name'] for c in inspector.get_columns('bookings')]
    if 'expires_at' not in columns:
        with op.batch_alter_table('bookings', schema=None) as batch_op:
            batch_op.add_column(sa.Column('expires_at', sa.DateTime(), nullable=True))


def downgrade():
    with op.batch_alter_table('bookings', schema=None) as batch_op:
        batch_op.drop_column('expires_at')
