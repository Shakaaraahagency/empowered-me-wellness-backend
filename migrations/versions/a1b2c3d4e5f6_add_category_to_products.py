"""add category column to products table

Revision ID: a1b2c3d4e5f6
Revises: 1e5678edd0bb
Create Date: 2026-08-11 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '1e5678edd0bb'
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    inspector = sa.inspect(conn)

    products_columns = [c['name'] for c in inspector.get_columns('products')]
    if 'category' not in products_columns:
        with op.batch_alter_table('products', schema=None) as batch_op:
            batch_op.add_column(sa.Column('category', sa.String(length=100), nullable=True, server_default='ebook'))


def downgrade():
    with op.batch_alter_table('products', schema=None) as batch_op:
        batch_op.drop_column('category')
