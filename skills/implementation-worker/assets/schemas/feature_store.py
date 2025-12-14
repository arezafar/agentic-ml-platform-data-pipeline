"""
Feature Store Schema - Hybrid JSONB Design

This module implements the Logical View (LOG-01) of the 4+1 Architectural Model.
It provides a hybrid schema that balances relational integrity with JSONB flexibility.

Key Patterns:
- Entity Identity: Relational (UUID) for joins and FK integrity
- Event Metadata: Relational (TIMESTAMPTZ) for time-series indexing
- Static Features: Relational columns for stable attributes
- Dynamic Features: JSONB for schema-on-read flexibility

TDD Task:
    Write test_schema_evolution.py that:
    1. Inserts a record with key A
    2. Inserts a record with key B
    3. Asserts both can be queried efficiently via GIN index
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Column,
    DateTime,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


class FeatureStore(Base):
    """
    Hybrid Feature Store Table
    
    Combines relational integrity for identifiers with JSONB flexibility
    for rapidly evolving feature vectors.
    
    Schema Design Rationale:
    - entity_id: UUID primary key for referential integrity
    - entity_type: Categorical identifier (user, product, session)
    - event_timestamp: When the event occurred (for time-travel queries)
    - created_at: When the record was inserted (for snapshot isolation)
    - static_features: Stable attributes in relational columns
    - dynamic_features: Experimental signals in JSONB
    
    Time-Travel Semantics:
        To ensure training data reproducibility, use:
        SELECT * FROM feature_store 
        WHERE created_at <= :snapshot_time
    """
    
    __tablename__ = "feature_store"
    
    # Primary Key - UUID for distributed systems compatibility
    entity_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Unique entity identifier"
    )
    
    # Entity Classification
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Entity category: user, product, session, etc."
    )
    
    # Temporal Metadata (Critical for Time-Travel)
    event_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
        comment="When the event occurred in the source system"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        index=True,
        comment="Record insertion time for snapshot isolation"
    )
    
    # Static Features - Stable attributes in relational columns
    # These provide optimized storage for high-cardinality, unchanging data
    country_code: Mapped[Optional[str]] = mapped_column(
        String(3),
        nullable=True,
        comment="ISO 3166-1 alpha-3 country code"
    )
    
    segment: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Business segment classification"
    )
    
    # Dynamic Features - JSONB for schema-on-read flexibility
    # Data scientists can push new features without DB migrations
    dynamic_features: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Experimental feature signals (schema-on-read)"
    )
    
    # Metadata
    source_system: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Origin system identifier"
    )
    
    feature_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="1.0.0",
        comment="Feature schema version for compatibility tracking"
    )
    
    # Table-level indexes
    __table_args__ = (
        # GIN index for JSONB containment queries
        # Uses jsonb_path_ops for better performance on @> operator
        Index(
            "ix_feature_store_dynamic_features_gin",
            dynamic_features,
            postgresql_using="gin",
            postgresql_ops={"dynamic_features": "jsonb_path_ops"}
        ),
        # Composite index for common query patterns
        Index(
            "ix_feature_store_entity_time",
            entity_type,
            event_timestamp.desc()
        ),
        # Partial index for snapshot isolation queries
        Index(
            "ix_feature_store_created_at_brin",
            created_at,
            postgresql_using="brin"  # Efficient for append-only time-series
        ),
        {
            "comment": "Hybrid feature store with JSONB for dynamic schema evolution"
        }
    )
    
    def __repr__(self) -> str:
        return (
            f"<FeatureStore(entity_id={self.entity_id}, "
            f"entity_type={self.entity_type}, "
            f"event_timestamp={self.event_timestamp})>"
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Export feature record as dictionary.
        
        Combines static and dynamic features into a flat structure
        suitable for ML model input.
        """
        base = {
            "entity_id": str(self.entity_id),
            "entity_type": self.entity_type,
            "event_timestamp": self.event_timestamp.isoformat(),
            "country_code": self.country_code,
            "segment": self.segment,
        }
        # Merge dynamic features
        base.update(self.dynamic_features or {})
        return base


# Query helper functions
def query_by_segment(session, segment: str):
    """
    Query features by segment using JSONB containment.
    
    Example:
        query_by_segment(session, "high_value")
    """
    return session.query(FeatureStore).filter(
        FeatureStore.dynamic_features.op("@>")('{"segment": "' + segment + '"}')
    )


def query_snapshot(session, snapshot_time: datetime):
    """
    Query features with point-in-time consistency.
    
    This ensures training data reproducibility by only returning
    records that existed at the specified snapshot time.
    
    Args:
        session: SQLAlchemy session
        snapshot_time: The point in time to query
        
    Returns:
        Query filtered to records created before snapshot_time
    """
    return session.query(FeatureStore).filter(
        FeatureStore.created_at <= snapshot_time
    )


def export_training_snapshot(session, snapshot_time: datetime, entity_type: str):
    """
    Export a frozen training dataset.
    
    This implements the Snapshot Isolation pattern from the Process View.
    The exported dataset is immutable and reproducible.
    
    Args:
        session: SQLAlchemy session
        snapshot_time: Point-in-time for snapshot
        entity_type: Filter by entity type
        
    Returns:
        List of feature dictionaries suitable for H2O Frame creation
    """
    records = (
        session.query(FeatureStore)
        .filter(
            FeatureStore.created_at <= snapshot_time,
            FeatureStore.entity_type == entity_type
        )
        .order_by(FeatureStore.event_timestamp)
        .all()
    )
    return [record.to_dict() for record in records]
