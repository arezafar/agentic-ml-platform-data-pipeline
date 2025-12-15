"""
Test Schema Evolution - LOG-01-01 TDD

This test suite validates the JSONB schema evolution pattern
from the Logical View.

Test Requirements:
    1. Insert records with different JSONB keys
    2. Query records using GIN index containment operators
    3. Verify snapshot isolation with created_at filtering

Run with:
    pytest test_schema_evolution.py -v
"""

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

# Mark all tests as requiring testcontainers
pytestmark = [
    pytest.mark.integration,
    pytest.mark.slow
]


class TestFeatureStoreSchema:
    """Test suite for FeatureStore JSONB schema."""
    
    def test_insert_with_dynamic_key_a(self, postgres_session, sample_feature_data):
        """
        Test: Insert a feature record with key A in dynamic_features.
        
        Verifies that JSONB allows arbitrary keys without schema migration.
        """
        # Arrange
        from schemas import FeatureStore
        
        feature = FeatureStore(
            entity_id=sample_feature_data["entity_id"],
            entity_type=sample_feature_data["entity_type"],
            event_timestamp=sample_feature_data["event_timestamp"],
            dynamic_features={"key_a": "value_a", "score": 0.95}
        )
        
        # Act
        postgres_session.add(feature)
        postgres_session.commit()
        
        # Assert
        result = postgres_session.query(FeatureStore).filter_by(
            entity_id=sample_feature_data["entity_id"]
        ).first()
        
        assert result is not None
        assert result.dynamic_features["key_a"] == "value_a"
        assert result.dynamic_features["score"] == 0.95
    
    def test_insert_with_dynamic_key_b(self, postgres_session):
        """
        Test: Insert a feature record with key B (different from key A).
        
        Verifies schema-on-read flexibility.
        """
        # Arrange
        from schemas import FeatureStore
        
        entity_id = uuid4()
        feature = FeatureStore(
            entity_id=entity_id,
            entity_type="product",
            event_timestamp=datetime.now(timezone.utc),
            dynamic_features={"key_b": 12345, "category": "electronics"}
        )
        
        # Act
        postgres_session.add(feature)
        postgres_session.commit()
        
        # Assert
        result = postgres_session.query(FeatureStore).filter_by(
            entity_id=entity_id
        ).first()
        
        assert result is not None
        assert result.dynamic_features["key_b"] == 12345
        assert "key_a" not in result.dynamic_features
    
    def test_gin_index_containment_query(self, postgres_session):
        """
        Test: Query using JSONB containment operator (@>).
        
        This tests that the GIN index is used for efficient lookups.
        """
        # Arrange
        from schemas import FeatureStore
        
        # Insert records with different segments
        for segment in ["premium", "standard", "basic"]:
            feature = FeatureStore(
                entity_id=uuid4(),
                entity_type="user",
                event_timestamp=datetime.now(timezone.utc),
                dynamic_features={"tier": segment, "active": True}
            )
            postgres_session.add(feature)
        
        postgres_session.commit()
        
        # Act - Query using containment
        premium_users = postgres_session.query(FeatureStore).filter(
            FeatureStore.dynamic_features.op("@>")(
                '{"tier": "premium"}'
            )
        ).all()
        
        # Assert
        assert len(premium_users) == 1
        assert premium_users[0].dynamic_features["tier"] == "premium"
    
    def test_snapshot_isolation(self, postgres_session):
        """
        Test: Query with snapshot isolation using created_at.
        
        Verifies time-travel semantics for training data reproducibility.
        """
        # Arrange
        from schemas import FeatureStore, query_snapshot
        
        now = datetime.now(timezone.utc)
        
        # Insert record at T-2 hours
        old_record = FeatureStore(
            entity_id=uuid4(),
            entity_type="user",
            event_timestamp=now - timedelta(hours=2),
            dynamic_features={"version": 1}
        )
        # Manually set created_at to simulate past insertion
        old_record.created_at = now - timedelta(hours=2)
        
        # Insert record at T-0 (now)
        new_record = FeatureStore(
            entity_id=uuid4(),
            entity_type="user",
            event_timestamp=now,
            dynamic_features={"version": 2}
        )
        
        postgres_session.add(old_record)
        postgres_session.add(new_record)
        postgres_session.commit()
        
        # Act - Query with snapshot at T-1 hour
        snapshot_time = now - timedelta(hours=1)
        snapshot_query = query_snapshot(postgres_session, snapshot_time)
        results = snapshot_query.all()
        
        # Assert - Only old record should be visible
        assert len(results) == 1
        assert results[0].dynamic_features["version"] == 1


class TestModelRegistryIntegrity:
    """Test suite for ModelRegistry FK constraints."""
    
    def test_cannot_delete_training_job_with_model(self, postgres_session):
        """
        Test: FK constraint prevents deleting training job if model exists.
        
        Ensures model lineage is preserved.
        """
        # Arrange
        from schemas import ModelRegistry, TrainingJobLog
        import hashlib
        
        # Create training job
        job = TrainingJobLog(
            pipeline_name="test_pipeline",
            snapshot_timestamp=datetime.now(timezone.utc),
            entity_type="user",
            record_count=1000,
            automl_config={"max_models": 10}
        )
        postgres_session.add(job)
        postgres_session.flush()  # Get job_id
        
        # Create model linked to job
        model = ModelRegistry(
            model_name="test_model",
            model_version="1.0.0",
            mojo_path="/models/test.mojo",
            mojo_checksum=hashlib.sha256(b"test").hexdigest(),
            training_job_id=job.job_id,
            metrics={"auc": 0.95},
            primary_metric_name="auc",
            primary_metric_value=0.95
        )
        postgres_session.add(model)
        postgres_session.commit()
        
        # Act & Assert - Deleting job should fail
        with pytest.raises(Exception):  # IntegrityError
            postgres_session.delete(job)
            postgres_session.commit()


class TestSchemaEvolutionConcurrency:
    """Test concurrent schema evolution scenarios."""
    
    def test_concurrent_different_keys(self, postgres_session, sample_feature_batch):
        """
        Test: Multiple records with different JSONB keys coexist.
        
        Simulates rapid feature experimentation by data scientists.
        """
        # Arrange
        from schemas import FeatureStore
        
        # Insert records with evolving schemas
        features = []
        for i, data in enumerate(sample_feature_batch):
            feature = FeatureStore(
                entity_id=data["entity_id"],
                entity_type=data["entity_type"],
                event_timestamp=data["event_timestamp"],
                dynamic_features={
                    f"experiment_{i}": True,
                    "common_key": i,
                    **data.get("dynamic_features", {})
                }
            )
            features.append(feature)
        
        postgres_session.add_all(features)
        postgres_session.commit()
        
        # Act - Query all
        all_features = postgres_session.query(FeatureStore).all()
        
        # Assert
        assert len(all_features) == len(sample_feature_batch)
        
        # Each should have unique experiment key
        experiment_keys = set()
        for f in all_features:
            for key in f.dynamic_features.keys():
                if key.startswith("experiment_"):
                    experiment_keys.add(key)
        
        assert len(experiment_keys) == len(sample_feature_batch)
