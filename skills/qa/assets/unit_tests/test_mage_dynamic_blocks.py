"""
QA Skill - Mage Dynamic Block Unit Tests

Implements test templates for tasks:
- UT-MAGE-01: Verify Dynamic Block Output Structure
- UT-MAGE-02: Validate Metadata UUID Uniqueness
- UT-MAGE-03: Verify Upstream State Isolation
- UT-MAGE-04: Mocking IO Libraries for Data Loaders

These tests verify Mage block contracts in isolation without
running the full orchestration engine.
"""

import re
from typing import Any
from unittest.mock import MagicMock, patch

import pytest


# =============================================================================
# UT-MAGE-01: Verify Dynamic Block Output Structure
# =============================================================================


class TestDynamicBlockOutputStructure:
    """
    Context: Dynamic blocks must return [data_list, metadata_list].
    Risk: Returning a flat list or tuple causes pipeline stagnation.
    """
    
    def test_returns_list_of_two_lists(self, mock_mage_context: dict):
        """
        Verify that dynamic block returns exactly [data_list, metadata_list].
        
        Acceptance Criteria:
        - Output type is List[List]
        - len(output) == 2
        - Both elements are lists
        """
        # ARRANGE: Import your dynamic block function
        # from your_pipeline.transformers.hyperparams_fanout import execute
        
        # Mock the block execution
        def mock_dynamic_block(*args, **kwargs) -> list[list]:
            data_list = [
                {"hyperparams": {"max_depth": 5}},
                {"hyperparams": {"max_depth": 10}},
                {"hyperparams": {"max_depth": 15}},
            ]
            metadata_list = [
                {"block_uuid": "tuning_depth_5"},
                {"block_uuid": "tuning_depth_10"},
                {"block_uuid": "tuning_depth_15"},
            ]
            return [data_list, metadata_list]
        
        # ACT
        result = mock_dynamic_block(**mock_mage_context)
        
        # ASSERT
        assert isinstance(result, list), "Output must be a list"
        assert len(result) == 2, "Dynamic block must return exactly 2 lists"
        assert isinstance(result[0], list), "First element (data) must be a list"
        assert isinstance(result[1], list), "Second element (metadata) must be a list"
    
    def test_data_and_metadata_lengths_match(self, mock_mage_context: dict):
        """
        Verify that data_list and metadata_list have equal lengths.
        
        Risk: Mismatch leads to data loss for specific fan-out branches.
        """
        # Mock dynamic block with mismatched lengths
        def mock_dynamic_block_mismatched() -> list[list]:
            data_list = [{"data": 1}, {"data": 2}, {"data": 3}]
            metadata_list = [{"block_uuid": "a"}, {"block_uuid": "b"}]  # Missing one!
            return [data_list, metadata_list]
        
        result = mock_dynamic_block_mismatched()
        
        # This assertion should FAIL for mismatched blocks
        assert len(result[0]) == len(result[1]), (
            f"Data list length ({len(result[0])}) must match "
            f"metadata list length ({len(result[1])})"
        )
    
    def test_metadata_contains_block_uuid(self, mock_mage_context: dict):
        """
        Verify each metadata dict contains required 'block_uuid' key.
        """
        metadata_list = [
            {"block_uuid": "task_1"},
            {"block_uuid": "task_2"},
            {"block_uuid": "task_3"},
        ]
        
        for i, metadata in enumerate(metadata_list):
            assert "block_uuid" in metadata, (
                f"Metadata at index {i} missing 'block_uuid' key"
            )


# =============================================================================
# UT-MAGE-02: Validate Metadata UUID Uniqueness
# =============================================================================


class TestMetadataUUIDUniqueness:
    """
    Context: Mage uses block_uuid to track state of dynamically spawned tasks.
    Risk: Collision results in state overwrites (last-write-wins).
    """
    
    def test_all_uuids_are_unique(self):
        """
        Collect all block_uuid values and verify uniqueness.
        """
        metadata_list = [
            {"block_uuid": "model_gbm_depth5"},
            {"block_uuid": "model_gbm_depth10"},
            {"block_uuid": "model_xgb_depth5"},
            {"block_uuid": "model_xgb_depth10"},
        ]
        
        uuids = [m["block_uuid"] for m in metadata_list]
        
        assert len(set(uuids)) == len(uuids), (
            f"Duplicate UUIDs found: {[u for u in uuids if uuids.count(u) > 1]}"
        )
    
    def test_uuids_are_url_safe(self):
        """
        Verify UUIDs are URL-safe and filesystem-compatible.
        
        Pattern: alphanumeric, underscores, hyphens only
        """
        metadata_list = [
            {"block_uuid": "model_v1_2024"},
            {"block_uuid": "training-run-001"},
            {"block_uuid": "hyperparams_grid_search"},
        ]
        
        url_safe_pattern = re.compile(r'^[a-zA-Z0-9_-]+$')
        
        for metadata in metadata_list:
            uuid = metadata["block_uuid"]
            assert url_safe_pattern.match(uuid), (
                f"UUID '{uuid}' contains invalid characters. "
                "Only alphanumeric, underscores, and hyphens allowed."
            )
    
    def test_detects_uuid_collision(self):
        """
        Negative test: Verify collision detection works.
        """
        metadata_list = [
            {"block_uuid": "model_A"},
            {"block_uuid": "model_B"},
            {"block_uuid": "model_A"},  # DUPLICATE!
        ]
        
        uuids = [m["block_uuid"] for m in metadata_list]
        
        with pytest.raises(AssertionError):
            assert len(set(uuids)) == len(uuids), "Duplicates detected"


# =============================================================================
# UT-MAGE-03: Verify Upstream State Isolation
# =============================================================================


class TestUpstreamStateIsolation:
    """
    Context: Blocks run in shared context but must not mutate global state.
    Risk: Side effects cause non-deterministic behavior in parallel workers.
    """
    
    def test_block_does_not_mutate_global_vars(self, mock_global_vars: dict):
        """
        Verify block does not modify the global_vars dictionary.
        """
        import copy
        
        original_vars = copy.deepcopy(mock_global_vars)
        
        # Simulate block execution that might mutate globals
        def mock_block_execution(global_vars: dict) -> Any:
            # BAD: Mutating global_vars
            # global_vars["new_key"] = "new_value"
            
            # GOOD: Reading only
            threshold = global_vars.get("performance_threshold", 0.8)
            return {"threshold_used": threshold}
        
        result = mock_block_execution(mock_global_vars)
        
        assert mock_global_vars == original_vars, (
            "Block mutated global_vars! This causes non-deterministic behavior."
        )
    
    def test_block_is_idempotent(self, sample_dataframe):
        """
        Verify that running block twice produces identical output.
        """
        import copy
        
        def mock_transformer(df):
            # Create a copy rather than mutating input
            result = df.copy()
            result["processed"] = True
            return result
        
        input_df = sample_dataframe.copy()
        
        result_1 = mock_transformer(input_df)
        result_2 = mock_transformer(input_df)
        
        # Both results should be equal
        assert result_1.equals(result_2), "Block is not idempotent"
        
        # Original input should be unchanged
        assert "processed" not in input_df.columns, (
            "Block mutated input DataFrame"
        )


# =============================================================================
# UT-MAGE-04: Mocking IO Libraries for Data Loaders
# =============================================================================


class TestDataLoaderMocking:
    """
    Context: Data Loaders connect to external APIs.
    Requirement: Use unittest.mock to simulate API responses.
    """
    
    def test_handles_rate_limit_gracefully(self, mock_requests):
        """
        Verify block handles HTTP 429 (Rate Limit) errors.
        """
        from unittest.mock import Mock
        
        # Configure mock to return 429
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.json.return_value = {"error": "rate limited"}
        mock_requests.return_value = mock_response
        
        def mock_data_loader_with_retry():
            import time
            
            response = mock_requests("https://api.example.com/data")
            
            if response.status_code == 429:
                # Implement retry logic
                time.sleep(0.01)  # Minimal sleep for test
                return {"status": "retried", "data": []}
            
            return response.json()
        
        result = mock_data_loader_with_retry()
        
        assert result.get("status") == "retried", (
            "Block should handle 429 with retry logic"
        )
    
    def test_handles_server_error(self, mock_requests):
        """
        Verify block handles HTTP 500 errors gracefully.
        """
        from unittest.mock import Mock
        
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Server Error")
        mock_requests.return_value = mock_response
        
        def mock_data_loader_with_error_handling():
            try:
                response = mock_requests("https://api.example.com/data")
                response.raise_for_status()
                return response.json()
            except Exception as e:
                # Graceful degradation
                return {"error": str(e), "data": []}
        
        result = mock_data_loader_with_error_handling()
        
        assert "error" in result, "Block should catch and handle 500 errors"
        assert result.get("data") == [], "Block should return empty data on error"
    
    def test_returns_dataframe_for_empty_response(self, mock_requests):
        """
        Verify block returns properly formatted DataFrame even for empty API responses.
        """
        import pandas as pd
        from unittest.mock import Mock
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}  # Empty response
        mock_requests.return_value = mock_response
        
        def mock_data_loader():
            response = mock_requests("https://api.example.com/data")
            items = response.json().get("items", [])
            
            if not items:
                # Return empty DataFrame with expected schema
                return pd.DataFrame(columns=["id", "value", "timestamp"])
            
            return pd.DataFrame(items)
        
        result = mock_data_loader()
        
        assert isinstance(result, pd.DataFrame), "Must return DataFrame"
        assert list(result.columns) == ["id", "value", "timestamp"], (
            "Empty DataFrame must preserve expected schema"
        )


# =============================================================================
# Dynamic Block Reduce Logic Tests
# =============================================================================


class TestReduceBlockLogic:
    """
    Verify the 'reduce' step where fan-out results are aggregated.
    Risk: Silent data loss if only first/last batch is exported.
    """
    
    def test_reduce_concatenates_all_dataframes(self):
        """
        Pass a list of DataFrames to reduce block and verify no row loss.
        """
        import pandas as pd
        
        # Simulate fan-out results (3 batches)
        batch_1 = pd.DataFrame({"id": [1, 2], "score": [0.9, 0.8]})
        batch_2 = pd.DataFrame({"id": [3, 4], "score": [0.7, 0.6]})
        batch_3 = pd.DataFrame({"id": [5, 6], "score": [0.5, 0.4]})
        
        fan_out_results = [batch_1, batch_2, batch_3]
        
        def reduce_block(dfs: list) -> pd.DataFrame:
            """Properly concatenate all fan-out results."""
            return pd.concat(dfs, ignore_index=True)
        
        result = reduce_block(fan_out_results)
        
        expected_rows = sum(len(df) for df in fan_out_results)
        
        assert len(result) == expected_rows, (
            f"Row count mismatch! Expected {expected_rows}, got {len(result)}. "
            "Possible data loss in reduce step."
        )
    
    def test_reduce_handles_empty_batches(self):
        """
        Verify reduce handles empty DataFrames without failing.
        """
        import pandas as pd
        
        batch_1 = pd.DataFrame({"id": [1, 2], "score": [0.9, 0.8]})
        batch_2 = pd.DataFrame(columns=["id", "score"])  # Empty batch
        batch_3 = pd.DataFrame({"id": [3], "score": [0.7]})
        
        fan_out_results = [batch_1, batch_2, batch_3]
        
        def reduce_block(dfs: list) -> pd.DataFrame:
            non_empty = [df for df in dfs if len(df) > 0]
            if not non_empty:
                return pd.DataFrame(columns=["id", "score"])
            return pd.concat(non_empty, ignore_index=True)
        
        result = reduce_block(fan_out_results)
        
        assert len(result) == 3, "Should have 3 rows (ignoring empty batch)"
