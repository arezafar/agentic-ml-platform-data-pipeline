"""
Alembic Migration: Create Feature Store Schema

Revision ID: 001
Create Date: 2024-01-01

This migration creates the feature_store table with:
- Hybrid JSONB schema for flexible feature evolution
- GIN index with jsonb_path_ops for efficient containment queries
- BRIN index for time-series snapshot queries
- Composite indexes for common query patterns

The Iron Law of TDD:
    Before running this migration, ensure test_schema_evolution.py passes.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_create_feature_store'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create feature_store table with optimized indexes."""
    
    # Create feature_store table
    op.create_table(
        'feature_store',
        sa.Column(
            'entity_id',
            postgresql.UUID(as_uuid=True),
            nullable=False,
            comment='Unique entity identifier'
        ),
        sa.Column(
            'entity_type',
            sa.String(50),
            nullable=False,
            comment='Entity category: user, product, session, etc.'
        ),
        sa.Column(
            'event_timestamp',
            sa.DateTime(timezone=True),
            nullable=False,
            comment='When the event occurred in the source system'
        ),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            comment='Record insertion time for snapshot isolation'
        ),
        sa.Column(
            'country_code',
            sa.String(3),
            nullable=True,
            comment='ISO 3166-1 alpha-3 country code'
        ),
        sa.Column(
            'segment',
            sa.String(50),
            nullable=True,
            comment='Business segment classification'
        ),
        sa.Column(
            'dynamic_features',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default='{}',
            comment='Experimental feature signals (schema-on-read)'
        ),
        sa.Column(
            'source_system',
            sa.String(100),
            nullable=True,
            comment='Origin system identifier'
        ),
        sa.Column(
            'feature_version',
            sa.String(20),
            nullable=False,
            server_default='1.0.0',
            comment='Feature schema version for compatibility tracking'
        ),
        sa.PrimaryKeyConstraint('entity_id'),
        comment='Hybrid feature store with JSONB for dynamic schema evolution'
    )
    
    # Standard B-tree indexes
    op.create_index(
        'ix_feature_store_entity_type',
        'feature_store',
        ['entity_type']
    )
    
    op.create_index(
        'ix_feature_store_event_timestamp',
        'feature_store',
        ['event_timestamp']
    )
    
    op.create_index(
        'ix_feature_store_segment',
        'feature_store',
        ['segment']
    )
    
    # Composite index for common query pattern
    op.create_index(
        'ix_feature_store_entity_time',
        'feature_store',
        ['entity_type', sa.text('event_timestamp DESC')]
    )
    
    # GIN index for JSONB containment queries
    # Uses jsonb_path_ops for better performance on @> operator
    # This enables queries like: WHERE dynamic_features @> '{"key": "value"}'
    op.execute("""
        CREATE INDEX ix_feature_store_dynamic_features_gin
        ON feature_store
        USING gin (dynamic_features jsonb_path_ops)
    """)
    
    # BRIN index for time-series data
    # Efficient for append-only tables with naturally ordered data
    op.execute("""
        CREATE INDEX ix_feature_store_created_at_brin
        ON feature_store
        USING brin (created_at)
    """)


def downgrade() -> None:
    """Drop feature_store table and all indexes."""
    
    # Drop indexes first
    op.drop_index('ix_feature_store_created_at_brin')
    op.drop_index('ix_feature_store_dynamic_features_gin')
    op.drop_index('ix_feature_store_entity_time')
    op.drop_index('ix_feature_store_segment')
    op.drop_index('ix_feature_store_event_timestamp')
    op.drop_index('ix_feature_store_entity_type')
    
    # Drop table
    op.drop_table('feature_store')
