"""Initial migration with applications, role_mappings, and custom_policies tables

Revision ID: 019cbf88d580
Revises: 
Create Date: 2025-11-07 17:42:40.163002

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '019cbf88d580'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create applications table
    op.create_table(
        'applications',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create custom_policies table
    op.create_table(
        'custom_policies',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=True),
        sa.Column('s3_key', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('creator_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create role_mappings table
    op.create_table(
        'role_mappings',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('application_id', sa.String(), nullable=False),
        sa.Column('environment', sa.String(), nullable=False),
        sa.Column('ad_group', sa.String(), nullable=False),
        sa.Column('role', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('application_id', 'environment', 'ad_group', name='uq_app_env_adgroup')
    )
    
    # Create indexes for role_mappings
    op.create_index('ix_role_mappings_application_id', 'role_mappings', ['application_id'])
    op.create_index('ix_role_mappings_ad_group', 'role_mappings', ['ad_group'])
    op.create_index('ix_role_mappings_environment', 'role_mappings', ['environment'])


def downgrade() -> None:
    # Drop indexes
    op.drop_index('ix_role_mappings_environment', table_name='role_mappings')
    op.drop_index('ix_role_mappings_ad_group', table_name='role_mappings')
    op.drop_index('ix_role_mappings_application_id', table_name='role_mappings')
    
    # Drop tables in reverse order
    op.drop_table('role_mappings')
    op.drop_table('custom_policies')
    op.drop_table('applications')
