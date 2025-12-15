"""
QA Skill - pgvector Dimensionality Tests

Additional specialized tests for pgvector dimension validation.

Implements task:
- UT-DB-02: Verify pgvector Dimensionality

These tests focus specifically on vector dimension consistency
required for pgvector column constraints.
"""

import os
from typing import Optional

import pytest


# =============================================================================
# Configuration
# =============================================================================

# Get expected dimensions from environment or use default
MODEL_DIMENSIONS = int(os.getenv("MODEL_DIMENSIONS", "128"))

# Common embedding model dimensions
KNOWN_DIMENSIONS = {
    "bert-base": 768,
    "bert-large": 1024,
    "sentence-transformers": 384,
    "openai-ada-002": 1536,
    "test": 128,
}


# =============================================================================
# Vector Validation Utilities
# =============================================================================


class VectorDimensionError(ValueError):
    """Raised when vector dimension doesn't match expected."""
    pass


def validate_vector_dimension(
    vector: list[float],
    expected: int = MODEL_DIMENSIONS,
    name: str = "vector"
) -> None:
    """
    Validate that a vector has the expected dimension.
    
    Args:
        vector: The vector to validate
        expected: Expected dimension count
        name: Name for error messages
    
    Raises:
        VectorDimensionError: If dimension doesn't match
    """
    if vector is None:
        raise VectorDimensionError(f"{name} is None")
    
    actual = len(vector)
    if actual != expected:
        raise VectorDimensionError(
            f"{name} has dimension {actual}, expected {expected}"
        )


def validate_vector_values(vector: list[float], name: str = "vector") -> None:
    """
    Validate that all vector values are valid floats.
    
    Checks for:
    - NaN values
    - Infinite values
    - Non-numeric types
    """
    import math
    
    for i, value in enumerate(vector):
        if not isinstance(value, (int, float)):
            raise ValueError(
                f"{name}[{i}] has invalid type: {type(value).__name__}"
            )
        
        if math.isnan(value):
            raise ValueError(f"{name}[{i}] is NaN")
        
        if math.isinf(value):
            raise ValueError(f"{name}[{i}] is infinite")


# =============================================================================
# Test Classes
# =============================================================================


class TestVectorDimensionValidation:
    """Tests for the validate_vector_dimension utility."""
    
    def test_valid_dimension_passes(self):
        """Vector with correct dimension should pass validation."""
        vector = [0.1] * MODEL_DIMENSIONS
        
        # Should not raise
        validate_vector_dimension(vector)
    
    def test_short_vector_fails(self):
        """Vector shorter than expected should fail."""
        short_vector = [0.1] * (MODEL_DIMENSIONS - 1)
        
        with pytest.raises(VectorDimensionError) as exc_info:
            validate_vector_dimension(short_vector)
        
        assert str(MODEL_DIMENSIONS - 1) in str(exc_info.value)
        assert str(MODEL_DIMENSIONS) in str(exc_info.value)
    
    def test_long_vector_fails(self):
        """Vector longer than expected should fail."""
        long_vector = [0.1] * (MODEL_DIMENSIONS + 1)
        
        with pytest.raises(VectorDimensionError) as exc_info:
            validate_vector_dimension(long_vector)
        
        assert str(MODEL_DIMENSIONS + 1) in str(exc_info.value)
    
    def test_empty_vector_fails(self):
        """Empty vector should fail."""
        empty_vector: list[float] = []
        
        with pytest.raises(VectorDimensionError):
            validate_vector_dimension(empty_vector)
    
    def test_none_vector_fails(self):
        """None vector should fail with appropriate error."""
        with pytest.raises(VectorDimensionError) as exc_info:
            validate_vector_dimension(None)  # type: ignore
        
        assert "None" in str(exc_info.value)
    
    def test_custom_dimension(self):
        """Test with custom expected dimension."""
        vector_768 = [0.1] * 768
        
        # Should pass with correct custom dimension
        validate_vector_dimension(vector_768, expected=768)
        
        # Should fail with wrong custom dimension
        with pytest.raises(VectorDimensionError):
            validate_vector_dimension(vector_768, expected=512)


class TestVectorValueValidation:
    """Tests for vector value validation."""
    
    def test_valid_floats_pass(self):
        """Vector with valid float values should pass."""
        vector = [0.1, -0.5, 1.0, 0.0, -1.0]
        
        # Should not raise
        validate_vector_values(vector)
    
    def test_integers_pass(self):
        """Vector with integer values should pass (auto-cast to float)."""
        vector = [1, 2, 3, 4, 5]
        
        # Should not raise
        validate_vector_values(vector)
    
    def test_nan_values_fail(self):
        """Vector containing NaN should fail."""
        import math
        
        vector = [0.1, 0.2, float("nan"), 0.4]
        
        with pytest.raises(ValueError) as exc_info:
            validate_vector_values(vector)
        
        assert "NaN" in str(exc_info.value)
    
    def test_infinite_values_fail(self):
        """Vector containing infinity should fail."""
        vector = [0.1, float("inf"), 0.3]
        
        with pytest.raises(ValueError) as exc_info:
            validate_vector_values(vector)
        
        assert "infinite" in str(exc_info.value)
    
    def test_negative_infinity_fails(self):
        """Vector containing negative infinity should fail."""
        vector = [0.1, float("-inf"), 0.3]
        
        with pytest.raises(ValueError):
            validate_vector_values(vector)
    
    def test_string_values_fail(self):
        """Vector containing strings should fail."""
        vector = [0.1, "0.2", 0.3]  # type: ignore
        
        with pytest.raises(ValueError) as exc_info:
            validate_vector_values(vector)
        
        assert "invalid type" in str(exc_info.value)
    
    def test_none_in_vector_fails(self):
        """Vector containing None should fail."""
        vector = [0.1, None, 0.3]  # type: ignore
        
        with pytest.raises(ValueError):
            validate_vector_values(vector)


class TestBatchVectorValidation:
    """Tests for validating batches of vectors."""
    
    def test_all_valid_vectors_pass(self, sample_feature_vectors):
        """All vectors in batch should have correct dimensions."""
        for i, vector in enumerate(sample_feature_vectors):
            validate_vector_dimension(vector, name=f"vector_{i}")
    
    def test_batch_dimension_consistency(self):
        """All vectors in a batch must have same dimension."""
        batch = [
            [0.1] * MODEL_DIMENSIONS,
            [0.2] * MODEL_DIMENSIONS,
            [0.3] * MODEL_DIMENSIONS,
        ]
        
        dimensions = [len(v) for v in batch]
        
        assert len(set(dimensions)) == 1, (
            f"Inconsistent dimensions in batch: {dimensions}"
        )
    
    def test_detect_inconsistent_batch(self):
        """Detect when batch has inconsistent dimensions."""
        inconsistent_batch = [
            [0.1] * MODEL_DIMENSIONS,
            [0.2] * (MODEL_DIMENSIONS + 1),  # Wrong dimension
            [0.3] * MODEL_DIMENSIONS,
        ]
        
        dimensions = [len(v) for v in inconsistent_batch]
        
        assert len(set(dimensions)) != 1, (
            "Should detect inconsistent dimensions"
        )


class TestEmbeddingModelDimensions:
    """Tests for common embedding model dimensions."""
    
    @pytest.mark.parametrize("model_name,expected_dim", [
        ("bert-base", 768),
        ("bert-large", 1024),
        ("sentence-transformers", 384),
        ("openai-ada-002", 1536),
    ])
    def test_known_model_dimensions(self, model_name: str, expected_dim: int):
        """Verify known embedding model dimensions."""
        # Simulate embedding from model
        mock_embedding = [0.1] * expected_dim
        
        assert len(mock_embedding) == KNOWN_DIMENSIONS[model_name], (
            f"Model {model_name} should produce {expected_dim}-dim embeddings"
        )
    
    def test_dimension_mismatch_detection(self):
        """
        Simulate scenario where model dimension doesn't match DB column.
        
        This is a critical error that causes PostgreSQL insert failures.
        """
        db_column_dimension = 768  # BERT-base
        model_output_dimension = 1536  # OpenAI ada-002
        
        mock_embedding = [0.1] * model_output_dimension
        
        with pytest.raises(VectorDimensionError):
            validate_vector_dimension(
                mock_embedding,
                expected=db_column_dimension,
                name="embedding"
            )


class TestVectorNormalization:
    """Tests for vector normalization (common pgvector requirement)."""
    
    def test_unit_vector_magnitude(self):
        """Verify normalized vectors have magnitude ≈ 1."""
        import math
        
        # Create a normalized vector
        raw = [1.0, 2.0, 3.0, 4.0]
        magnitude = math.sqrt(sum(x**2 for x in raw))
        normalized = [x / magnitude for x in raw]
        
        # Verify magnitude is 1
        result_magnitude = math.sqrt(sum(x**2 for x in normalized))
        
        assert abs(result_magnitude - 1.0) < 1e-10, (
            f"Normalized vector magnitude should be 1, got {result_magnitude}"
        )
    
    def test_zero_vector_normalization(self):
        """Zero vector cannot be normalized (division by zero)."""
        zero_vector = [0.0, 0.0, 0.0, 0.0]
        
        magnitude = sum(x**2 for x in zero_vector) ** 0.5
        
        assert magnitude == 0, "Zero vector has zero magnitude"
        
        # Attempting to normalize would cause division by zero
        with pytest.raises(ZeroDivisionError):
            normalized = [x / magnitude for x in zero_vector]
