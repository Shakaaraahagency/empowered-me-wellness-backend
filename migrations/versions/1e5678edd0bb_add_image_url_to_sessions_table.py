"""add image_url to sessions table

Revision ID: 1e5678edd0bb
Revises: d342ed33e4c3
Create Date: 2026-08-09 22:55:44.855831

"""
from alembic import op
import sqlalchemy as sa
import models.types


# revision identifiers, used by Alembic.
revision = '1e5678edd0bb'
down_revision = 'd342ed33e4c3'
branch_labels = None
depends_on = None


def upgrade():
    # Add image_url column to sessions table.
    # NOTE: the ix_newsletter_subscribers_email index is already created in
    # migration 3153c4f2f879 and must NOT be recreated here.
    with op.batch_alter_table('sessions', schema=None) as batch_op:
        batch_op.add_column(sa.Column('image_url', sa.String(length=500), nullable=True))


def downgrade():
    with op.batch_alter_table('sessions', schema=None) as batch_op:
        batch_op.drop_column('image_url')
