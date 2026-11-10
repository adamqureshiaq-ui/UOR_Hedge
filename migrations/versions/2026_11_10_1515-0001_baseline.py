"""Baseline: every table as Base.metadata.create_all() made it before migrations existed.

Databases created before this migration are marked as already being here (see upgrade_database in
database.py) instead of running it.

Revision ID: 0001_baseline
Revises: 
Create Date: 2026-11-10 15:19:22.043580

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '0001_baseline'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('applied_corporate_actions',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('kind', sa.String(), nullable=False),
    sa.Column('symbol', sa.String(), nullable=False),
    sa.Column('ex_date', sa.Date(), nullable=False),
    sa.Column('applied_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('corporate_actions_checkpoints',
    sa.Column('kind', sa.String(), nullable=False),
    sa.Column('checked_through', sa.Date(), nullable=False),
    sa.PrimaryKeyConstraint('kind')
    )
    op.create_table('users',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('username', sa.String(), nullable=False),
    sa.Column('email', sa.String(), nullable=False),
    sa.Column('hashed_password', sa.String(), nullable=False),
    sa.Column('cash_balance', sa.Numeric(precision=14, scale=2), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)

    op.create_table('pending_dividends',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('action_id', sa.String(), nullable=False),
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('symbol', sa.String(), nullable=False),
    sa.Column('shares', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('cash_per_share', sa.Numeric(precision=14, scale=6), nullable=False),
    sa.Column('amount', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('ex_date', sa.Date(), nullable=False),
    sa.Column('payable_date', sa.Date(), nullable=False),
    sa.Column('paid_at', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['action_id'], ['applied_corporate_actions.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('action_id', 'user_id')
    )
    op.create_table('portfolios',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('symbol', sa.String(), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('average_buy_price', sa.Numeric(precision=18, scale=2), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_portfolios_symbol'), 'portfolios', ['symbol'], unique=False)

    op.create_table('transactions',
    sa.Column('id', sa.String(), nullable=False),
    sa.Column('user_id', sa.String(), nullable=False),
    sa.Column('symbol', sa.String(), nullable=False),
    sa.Column('order_type', sa.String(), nullable=False),
    sa.Column('quantity', sa.Numeric(precision=18, scale=6), nullable=False),
    sa.Column('price_per_share', sa.Numeric(precision=14, scale=4), nullable=False),
    sa.Column('total_amount', sa.Numeric(precision=14, scale=2), nullable=False),
    sa.Column('timestamp', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('transactions')
    op.drop_index(op.f('ix_portfolios_symbol'), table_name='portfolios')

    op.drop_table('portfolios')
    op.drop_table('pending_dividends')
    op.drop_index(op.f('ix_users_username'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')

    op.drop_table('users')
    op.drop_table('corporate_actions_checkpoints')
    op.drop_table('applied_corporate_actions')