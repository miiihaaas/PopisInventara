"""Dodavanje FK constrainta za category i depreciation_rate u single_item tabeli

Revision ID: 6c1c8489c450
Revises: ed06b0307a96
Create Date: 2024-10-29 21:45:00.000000
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '6c1c8489c450'
down_revision = 'ed06b0307a96'
branch_labels = None
depends_on = None

def upgrade():
    # Prvo kopiramo podatke iz item tabele u single_item
    op.execute("""
        UPDATE single_item 
        SET category_id = (
            SELECT category_id 
            FROM item 
            WHERE item.id = single_item.item_id
        ),
        depreciation_rate_id = (
            SELECT depreciation_rate_id 
            FROM item 
            WHERE item.id = single_item.item_id
        )
        WHERE item_id IS NOT NULL
        AND category_id IS NULL
        AND depreciation_rate_id IS NULL
    """)
    
    # Zatim dodajemo foreign key constrainte
    with op.batch_alter_table('single_item', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'fk_single_item_category', 
            'category', 
            ['category_id'], ['id']
        )
        batch_op.create_foreign_key(
            'fk_single_item_depreciation_rate', 
            'depreciation_rate', 
            ['depreciation_rate_id'], ['id']
        )

def downgrade():
    with op.batch_alter_table('single_item', schema=None) as batch_op:
        batch_op.drop_constraint('fk_single_item_depreciation_rate', type_='foreignkey')
        batch_op.drop_constraint('fk_single_item_category', type_='foreignkey')