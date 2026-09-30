"""add file_url to products table

Revision ID: c6d7e8f9a0b1
Revises: 5bb03f99b2b1
Create Date: 2026-09-30 13:10:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c6d7e8f9a0b1'
down_revision = '5bb03f99b2b1'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    products_columns = [c['name'] for c in inspector.get_columns('products')]
    if 'file_url' not in products_columns:
        with op.batch_alter_table('products', schema=None) as batch_op:
            batch_op.add_column(sa.Column('file_url', sa.String(length=1000), nullable=True))


def downgrade():
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.drop_column('file_url')
