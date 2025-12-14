"""
Model Registry Schema - LOG-01-02

This module implements the Model Registry table for the Logical View.
It links MOJO artifacts to their training data versions for reproducibility.

Key Features:
- Model versioning with semantic versioning
- Foreign key to training job logs
- JSONB for flexible metrics storage
- Audit trail for model lifecycle

TDD Task:
    Write test_registry_integrity.py that:
    1. Creates a training job log
    2. Registers a model linked to that job
    3. Asserts FK constraints prevent orphaned models
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    String,
    Text,
    Float,
    Integer,
    Enum,
    UniqueConstraint,
    CheckConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

# Import Base from feature_store for consistency
from .feature_store import Base


class ModelStatus(enum.Enum):
    """Model lifecycle states."""
    TRAINING = "training"
    VALIDATING = "validating"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"
    FAILED = "failed"


class TrainingJobLog(Base):
    """
    Training Job Log Table
    
    Records each training run for reproducibility and auditing.
    Models reference this table to track their lineage.
    """
    
    __tablename__ = "training_job_log"
    
    job_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Unique job identifier"
    )
    
    # Training Configuration
    pipeline_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Mage pipeline that triggered training"
    )
    
    pipeline_run_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Mage execution run ID"
    )
    
    # Data Snapshot Reference
    snapshot_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Point-in-time for training data snapshot"
    )
    
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Entity type used for training"
    )
    
    record_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of records in training set"
    )
    
    # H2O Configuration
    h2o_cluster_id: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="H2O cluster identifier"
    )
    
    automl_config: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="H2O AutoML configuration parameters"
    )
    
    # Execution Metadata
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        comment="Job start time"
    )
    
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Job completion time"
    )
    
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="running",
        comment="Job status: running, completed, failed"
    )
    
    error_message: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Error details if job failed"
    )
    
    # Relationships
    models = relationship("ModelRegistry", back_populates="training_job")
    
    __table_args__ = (
        {"comment": "Audit log of all model training runs"}
    )


class ModelRegistry(Base):
    """
    Model Registry Table
    
    Central registry for all deployed models with version tracking,
    performance metrics, and production lifecycle management.
    
    Key Patterns:
    - Semantic versioning for model iterations
    - JSONB metrics for flexible performance storage
    - FK to TrainingJobLog for complete lineage
    - Status enum for lifecycle tracking
    """
    
    __tablename__ = "model_registry"
    
    # Primary Key
    model_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        comment="Unique model identifier"
    )
    
    # Model Identity
    model_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
        comment="Human-readable model name"
    )
    
    model_version: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Semantic version (e.g., 1.2.3)"
    )
    
    # MOJO Artifact Location
    mojo_path: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        unique=True,
        comment="Path to MOJO artifact (NOT POJO - forbidden)"
    )
    
    mojo_checksum: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="SHA-256 checksum for integrity verification"
    )
    
    # Training Lineage (FK to TrainingJobLog)
    training_job_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("training_job_log.job_id", ondelete="RESTRICT"),
        nullable=False,
        comment="Reference to training job (cannot delete job if model exists)"
    )
    
    # Performance Metrics
    metrics: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Model performance metrics (AUC, RMSE, etc.)"
    )
    
    # Primary metric for comparison
    primary_metric_name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Name of the primary evaluation metric"
    )
    
    primary_metric_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
        comment="Value of the primary metric"
    )
    
    # Lifecycle Status
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="staging",
        comment="Model status: staging, production, archived"
    )
    
    # Deployment Metadata
    deployed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When model was deployed to production"
    )
    
    deployed_by: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="User/system that deployed the model"
    )
    
    # Audit Fields
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now()
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )
    
    # Relationships
    training_job = relationship("TrainingJobLog", back_populates="models")
    
    __table_args__ = (
        # Unique constraint on name + version
        UniqueConstraint(
            "model_name", "model_version",
            name="uq_model_name_version"
        ),
        # Check constraint: only one production model per name
        CheckConstraint(
            "status != 'production' OR deployed_at IS NOT NULL",
            name="ck_production_requires_deployment"
        ),
        {"comment": "Central registry for MOJO model artifacts"}
    )
    
    def __repr__(self) -> str:
        return (
            f"<ModelRegistry(model_id={self.model_id}, "
            f"name={self.model_name}, version={self.model_version}, "
            f"status={self.status})>"
        )
    
    def promote_to_production(self, deployed_by: str) -> None:
        """
        Promote model to production status.
        
        This should be called within a transaction that also
        demotes the current production model.
        """
        self.status = "production"
        self.deployed_at = datetime.utcnow()
        self.deployed_by = deployed_by


# Helper functions for model management
def get_production_model(session, model_name: str):
    """Get the current production model for a given name."""
    return (
        session.query(ModelRegistry)
        .filter(
            ModelRegistry.model_name == model_name,
            ModelRegistry.status == "production"
        )
        .first()
    )


def register_model(
    session,
    model_name: str,
    model_version: str,
    mojo_path: str,
    mojo_checksum: str,
    training_job_id: UUID,
    metrics: Dict[str, Any],
    primary_metric_name: str
) -> ModelRegistry:
    """
    Register a new model in the registry.
    
    The model starts in 'staging' status and must be
    explicitly promoted to production.
    """
    model = ModelRegistry(
        model_name=model_name,
        model_version=model_version,
        mojo_path=mojo_path,
        mojo_checksum=mojo_checksum,
        training_job_id=training_job_id,
        metrics=metrics,
        primary_metric_name=primary_metric_name,
        primary_metric_value=metrics.get(primary_metric_name, 0.0),
        status="staging"
    )
    session.add(model)
    return model
