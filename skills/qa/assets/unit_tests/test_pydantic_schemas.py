"""
QA Skill - Pydantic Schema Unit Tests

Implements test templates for tasks:
- UT-DB-01: Validate Feature Vector Integrity (JSONB)
- UT-DB-02: Verify pgvector Dimensionality
- UT-DB-03: Validate JSONB Indexing Paths
- UT-DB-04: Test Schema Evolution (Migration)

These tests verify Pydantic schema enforcement and
PostgreSQL JSONB compatibility.
"""

import json
import os
from typing import Any, Optional

import pytest
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


# =============================================================================
# Sample Pydantic Models for Testing
# =============================================================================


class FeatureVector(BaseModel):
    """
    Feature vector schema with strict type enforcement.
    
    Used for storing ML features in PostgreSQL JSONB columns.
    """
    model_config = ConfigDict(strict=True)
    
    user_id: str
    segment: str
    features: list[float]
    embedding: Optional[list[float]] = None
    metadata: Optional[dict[str, Any]] = None
    
    @field_validator("features", "embedding", mode="before")
    @classmethod
    def ensure_float_list(cls, v):
        """Ensure all vector values are floats."""
        if v is None:
            return v
        return [float(x) for x in v]


class FeatureVectorLegacy(BaseModel):
    """
    Legacy schema for migration testing (lacks 'segment' field).
    """
    user_id: str
    features: list[float]


# =============================================================================
# UT-DB-01: Validate Feature Vector Integrity (JSONB)
# =============================================================================


class TestFeatureVectorIntegrity:
    """
    Context: Feature vectors stored in JSONB must be consumed as 
    dense numerical arrays by H2O.
    
    Risk: If a feature is stored as a string ("0.5") instead of 
    float (0.5), the H2O C++ runtime will fail or misinterpret.
    """
    
    def test_accepts_valid_float_features(self):
        """Verify valid float inputs are accepted."""
        data = {
            "user_id": "user_123",
            "segment": "high_value",
            "features": [0.1, 0.2, 0.3, 0.4, 0.5],
        }
        
        fv = FeatureVector(**data)
        
        assert all(isinstance(f, float) for f in fv.features)
        assert fv.features == [0.1, 0.2, 0.3, 0.4, 0.5]
    
    def test_casts_integers_to_floats(self):
        """Verify integers are properly cast to floats."""
        data = {
            "user_id": "user_123",
            "segment": "high_value",
            "features": [1, 2, 3, 4, 5],  # Integers
        }
        
        fv = FeatureVector(**data)
        
        assert all(isinstance(f, float) for f in fv.features)
        assert fv.features == [1.0, 2.0, 3.0, 4.0, 5.0]
    
    def test_casts_numeric_strings_to_floats(self):
        """
        Verify numeric strings are cast to floats by validator.
        
        Note: With strict=True, this would fail without the validator.
        """
        data = {
            "user_id": "user_123",
            "segment": "high_value",
            "features": ["0.1", "0.2", "0.3"],  # String values
        }
        
        fv = FeatureVector(**data)
        
        assert fv.features == [0.1, 0.2, 0.3]
    
    def test_rejects_non_numeric_values(self):
        """Verify non-numeric strings cause validation errors."""
        data = {
            "user_id": "user_123",
            "segment": "high_value",
            "features": ["invalid", "not_a_number"],
        }
        
        with pytest.raises((ValidationError, ValueError)):
            FeatureVector(**data)
    
    def test_json_serialization_preserves_precision(self):
        """
        Verify that JSON serialization preserves numerical precision.
        
        Risk: Floating point precision loss during serialization.
        """
        original_features = [0.123456789012345, 1e-10, 1e10]
        
        fv = FeatureVector(
            user_id="user_123",
            segment="test",
            features=original_features,
        )
        
        # Serialize and deserialize
        json_str = fv.model_dump_json()
        restored = FeatureVector.model_validate_json(json_str)
        
        # Check precision preserved (within floating point tolerance)
        for orig, restored_val in zip(original_features, restored.features):
            assert abs(orig - restored_val) < 1e-15, (
                f"Precision loss: {orig} -> {restored_val}"
            )


# =============================================================================
# UT-DB-02: Verify pgvector Dimensionality
# =============================================================================


class TestPgvectorDimensionality:
    """
    Context: The pgvector extension enforces fixed dimensions on vector columns.
    Risk: Inserting a 127-dimensional vector into a 128-dimensional index 
    causes a database-level error.
    """
    
    # Expected embedding dimension (e.g., 768 for BERT, 128 for testing)
    MODEL_DIMENSIONS = int(os.getenv("MODEL_DIMENSIONS", "128"))
    
    def test_vector_matches_expected_dimension(self, sample_feature_vectors):
        """Verify all vectors match MODEL_DIMENSIONS constant."""
        for i, vector in enumerate(sample_feature_vectors):
            assert len(vector) == self.MODEL_DIMENSIONS, (
                f"Vector {i} has dimension {len(vector)}, "
                f"expected {self.MODEL_DIMENSIONS}"
            )
    
    def test_detects_dimension_mismatch(self):
        """Negative test: Detect incorrect dimensions."""
        wrong_dimension_vector = [0.1] * (self.MODEL_DIMENSIONS - 1)
        
        with pytest.raises(AssertionError):
            assert len(wrong_dimension_vector) == self.MODEL_DIMENSIONS
    
    def test_handles_empty_vector(self):
        """Verify empty vectors are caught."""
        empty_vector: list[float] = []
        
        assert len(empty_vector) != self.MODEL_DIMENSIONS, (
            "Empty vector should not match expected dimensions"
        )
    
    def test_handles_null_vector(self):
        """Verify null/None vectors are handled properly."""
        fv = FeatureVector(
            user_id="user_123",
            segment="test",
            features=[0.1, 0.2, 0.3],
            embedding=None,  # Null embedding
        )
        
        assert fv.embedding is None
        # Should not raise validation error


class EmbeddingGenerator:
    """Mock embedding generator for testing dimension consistency."""
    
    def __init__(self, dimensions: int):
        self.dimensions = dimensions
    
    def generate(self, text: str) -> list[float]:
        """Generate a fixed-dimension embedding."""
        import hashlib
        
        # Deterministic pseudo-random based on input
        hash_bytes = hashlib.sha256(text.encode()).digest()
        
        # Generate consistent dimension output
        result = []
        for i in range(self.dimensions):
            byte_idx = i % len(hash_bytes)
            result.append(hash_bytes[byte_idx] / 255.0)
        
        return result


class TestEmbeddingDimensionConsistency:
    """Test embedding generation produces consistent dimensions."""
    
    DIMENSIONS = int(os.getenv("MODEL_DIMENSIONS", "128"))
    
    def test_generator_produces_correct_dimensions(self):
        """Verify embedding generator output matches expected dimensions."""
        generator = EmbeddingGenerator(dimensions=self.DIMENSIONS)
        
        test_inputs = [
            "Hello, world!",
            "This is a test sentence.",
            "",  # Edge case: empty string
            "A" * 10000,  # Edge case: very long string
        ]
        
        for text in test_inputs:
            embedding = generator.generate(text)
            assert len(embedding) == self.DIMENSIONS, (
                f"Embedding for '{text[:20]}...' has wrong dimension: "
                f"{len(embedding)} != {self.DIMENSIONS}"
            )


# =============================================================================
# UT-DB-03: Validate JSONB Indexing Paths
# =============================================================================


class TestJSONBIndexingPaths:
    """
    Context: Efficient retrieval depends on GIN indexes on specific JSON keys.
    Risk: Deeply nested keys not covered by GIN index trigger full table scans.
    """
    
    # Keys that should be at the top level for GIN index coverage
    INDEXED_KEYS = {"user_id", "segment"}
    
    def test_critical_fields_at_top_level(self):
        """Verify query fields are at top level of JSON structure."""
        fv = FeatureVector(
            user_id="user_123",
            segment="premium",
            features=[0.1, 0.2, 0.3],
        )
        
        # Get the JSON representation
        json_dict = fv.model_dump()
        
        for key in self.INDEXED_KEYS:
            assert key in json_dict, (
                f"Critical field '{key}' must be at top level for GIN indexing"
            )
            # Verify it's directly accessible (not nested)
            value = json_dict[key]
            assert not isinstance(value, dict), (
                f"Field '{key}' should be a primitive, not nested object"
            )
    
    def test_pydantic_structure_mirrors_gin_index(self):
        """
        Verify Pydantic model structure aligns with expected GIN index.
        
        GIN index definition (example):
        CREATE INDEX idx_features_gin ON features USING GIN ((data->'user_id'), (data->'segment'));
        """
        model_fields = set(FeatureVector.model_fields.keys())
        
        # All indexed keys must exist in model
        missing_fields = self.INDEXED_KEYS - model_fields
        
        assert not missing_fields, (
            f"Model missing indexed fields: {missing_fields}. "
            "GIN index will not cover these queries."
        )


# =============================================================================
# UT-DB-04: Test Schema Evolution (Migration)
# =============================================================================


class TestSchemaEvolution:
    """
    Context: Feature definitions change over time.
    Risk: New mandatory fields in Pydantic models cause read errors 
    for old data stored in PostgreSQL.
    """
    
    def test_new_schema_reads_old_data(self):
        """
        Create old JSON data and verify new schema handles it.
        
        Scenario: 'segment' field added in v2, but old data lacks it.
        """
        # Old data format (missing 'segment' field)
        old_data = {
            "user_id": "user_123",
            "features": [0.1, 0.2, 0.3],
        }
        
        # New schema with 'segment' as Optional with default
        class FeatureVectorV2(BaseModel):
            user_id: str
            segment: str = "unknown"  # Default for migration
            features: list[float]
        
        # Should load without error due to default value
        fv = FeatureVectorV2(**old_data)
        
        assert fv.segment == "unknown", (
            "Migration should use default value for missing field"
        )
    
    def test_mandatory_field_fails_on_old_data(self):
        """
        Negative test: Mandatory new fields break backward compatibility.
        """
        old_data = {
            "user_id": "user_123",
            "features": [0.1, 0.2, 0.3],
        }
        
        # New schema with MANDATORY 'segment' field
        class FeatureVectorBreaking(BaseModel):
            user_id: str
            segment: str  # No default - BREAKING CHANGE
            features: list[float]
        
        with pytest.raises(ValidationError) as exc_info:
            FeatureVectorBreaking(**old_data)
        
        # Verify the error is about 'segment'
        errors = exc_info.value.errors()
        field_names = [e["loc"][0] for e in errors]
        assert "segment" in field_names
    
    def test_optional_fields_handle_null(self):
        """
        Verify Optional fields with None work correctly.
        """
        data_with_nulls = {
            "user_id": "user_123",
            "segment": "test",
            "features": [0.1, 0.2],
            "embedding": None,
            "metadata": None,
        }
        
        fv = FeatureVector(**data_with_nulls)
        
        assert fv.embedding is None
        assert fv.metadata is None
    
    def test_extra_fields_ignored_or_captured(self):
        """
        Test behavior when old data has fields removed in new schema.
        """
        data_with_extra = {
            "user_id": "user_123",
            "segment": "test",
            "features": [0.1, 0.2],
            "legacy_field": "this was removed",  # Not in current schema
        }
        
        # By default, Pydantic ignores extra fields
        fv = FeatureVector(**data_with_extra)
        
        # Should not have the extra field
        assert not hasattr(fv, "legacy_field")
    
    def test_migration_preserves_data_integrity(self):
        """
        End-to-end test: Old JSON -> New Model -> JSON -> Verify
        """
        import json
        
        # Simulate reading old JSON from database
        old_json = '{"user_id": "user_123", "features": [0.5, 0.6, 0.7]}'
        old_data = json.loads(old_json)
        
        # Add default for missing required field
        if "segment" not in old_data:
            old_data["segment"] = "migrated"
        
        # Create new model instance
        fv = FeatureVector(**old_data)
        
        # Serialize back to JSON
        new_json = fv.model_dump_json()
        
        # Reload and verify
        reloaded = FeatureVector.model_validate_json(new_json)
        
        assert reloaded.user_id == "user_123"
        assert reloaded.features == [0.5, 0.6, 0.7]
        assert reloaded.segment == "migrated"
