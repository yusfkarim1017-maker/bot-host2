"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'bots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token', sa.String(length=255), nullable=False),
        sa.Column('username', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('mode', sa.Enum('webhook', 'polling', name='botmode'), nullable=False, server_default='polling'),
        sa.Column('owner_id', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token'),
    )
    op.create_index('ix_bots_is_active', 'bots', ['is_active'], unique=False)
    op.create_index('ix_bots_owner_id', 'bots', ['owner_id'], unique=False)

    op.create_table(
        'bot_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('bot_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('level', sa.String(length=20), nullable=False, server_default='info'),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), nullable=False, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['bot_id'], ['bots.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_bot_logs_bot_id_timestamp', 'bot_logs', ['bot_id', 'timestamp'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_bot_logs_bot_id_timestamp', table_name='bot_logs')
    op.drop_table('bot_logs')
    op.drop_index('ix_bots_owner_id', table_name='bots')
    op.drop_index('ix_bots_is_active', table_name='bots')
    op.drop_table('bots')
    op.execute("DROP TYPE IF EXISTS botmode")