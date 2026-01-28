"""Dodavanje date_in_use polja u single_item tabelu za praćenje datuma puštanja u upotrebu

Revision ID: a1b2c3d4e5f6
Revises: 6c1c8489c450
Create Date: 2026-01-28 15:30:00.000000
"""
from alembic import op
import sqlalchemy as sa
from datetime import date

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '9eefff3e4898'
branch_labels = None
depends_on = None

def upgrade():
    # Dodavanje nove kolone date_in_use
    with op.batch_alter_table('single_item', schema=None) as batch_op:
        batch_op.add_column(sa.Column('date_in_use', sa.Date(), nullable=True))
    
    # Migracija postojećih podataka:
    # - Predmeti u magacinu novih (room_id=6) dobijaju NULL (nisu još pušteni u upotrebu)
    # - Svi ostali predmeti dobijaju purchase_date kao date_in_use (pretpostavka: bili su u upotrebi od nabavke)
    op.execute("""
        UPDATE single_item 
        SET date_in_use = purchase_date
        WHERE room_id != 6
    """)

def downgrade():
    with op.batch_alter_table('single_item', schema=None) as batch_op:
        batch_op.drop_column('date_in_use')
