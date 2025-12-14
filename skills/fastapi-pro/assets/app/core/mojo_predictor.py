"""
Job 1: High-Concurrency MOJO Predictor

Implements the async/sync impedance bridge for H2O model inference.
Uses thread pool offloading to prevent event loop blocking.

Key Patterns:
- run_in_threadpool for CPU-bound inference
- C++ MOJO runtime (daimojo) over JVM for efficiency
- Pydantic validation before scoring

Success Criteria:
- 1,000 RPS throughput
- <50ms P99 latency
- No event loop blocking
"""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import json
import hashlib

# Thread pool for CPU-bound inference
_INFERENCE_EXECUTOR: Optional[ThreadPoolExecutor] = None


def get_inference_executor(max_workers: int = 4) -> ThreadPoolExecutor:
    """Get or create the inference thread pool."""
    global _INFERENCE_EXECUTOR
    if _INFERENCE_EXECUTOR is None:
        _INFERENCE_EXECUTOR = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="mojo_inference"
        )
    return _INFERENCE_EXECUTOR


class MojoPredictor:
    """
    High-performance MOJO model predictor with thread pool offloading.
    
    CRITICAL: Do NOT use h2o.init() within FastAPI. This would start
    a full H2O cluster node and destroy latency. Instead, use the
    C++ MOJO runtime via daimojo or h2o.mojo_predict_pandas.
    """
    
    def __init__(
        self,
        model_path: str,
        genmodel_path: Optional[str] = None,
        version: str = "latest",
    ):
        """
        Initialize the MOJO predictor.
        
        Args:
            model_path: Path to .mojo file
            genmodel_path: Path to h2o-genmodel.jar (optional for C++ runtime)
            version: Model version for cache invalidation
        """
        self.model_path = Path(model_path)
        self.genmodel_path = Path(genmodel_path) if genmodel_path else None
        self.version = version
        self._model = None
        self._loaded_at: Optional[datetime] = None
        
        # Validate model exists
        if not self.model_path.exists():
            raise FileNotFoundError(f"MOJO not found: {model_path}")
        
        self._load_model()
    
    def _load_model(self) -> None:
        """
        Load the MOJO model into memory.
        
        Uses the C++ runtime when available for optimal performance.
        Falls back to h2o.mojo_predict_pandas if daimojo not available.
        """
        print(f"[MOJO] Loading model: {self.model_path}")
        
        try:
            # Prefer C++ runtime (daimojo) for best performance
            import daimojo
            self._model = daimojo.load_model(str(self.model_path))
            self._runtime = "daimojo"
            print("[MOJO] Using daimojo (C++ runtime)")
            
        except ImportError:
            # Fallback to h2o.mojo_predict_pandas
            try:
                import h2o
                # Don't h2o.init() - just mark model path for predict_pandas
                self._model = str(self.model_path)
                self._runtime = "h2o_pandas"
                print("[MOJO] Using h2o.mojo_predict_pandas (JVM runtime)")
                
            except ImportError:
                # Mock mode for testing
                self._model = None
                self._runtime = "mock"
                print("[MOJO] ⚠️ No H2O runtime available. Using mock mode.")
        
        self._loaded_at = datetime.utcnow()
    
    def predict_sync(self, features: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronous prediction - to be called from thread pool.
        
        NEVER call this directly from an async endpoint.
        Use predict_async() instead.
        """
        import pandas as pd
        
        start_time = datetime.utcnow()
        
        # Convert to DataFrame
        if isinstance(features, dict):
            df = pd.DataFrame([features])
        elif isinstance(features, list):
            df = pd.DataFrame(features)
        else:
            df = features
        
        # Execute prediction based on runtime
        if self._runtime == "daimojo":
            predictions = self._model.predict(df)
            result = predictions.to_dict('records')
            
        elif self._runtime == "h2o_pandas":
            import h2o
            predictions = h2o.mojo_predict_pandas(
                dataframe=df,
                mojo_zip_path=self._model,
                genmodel_jar_path=str(self.genmodel_path) if self.genmodel_path else None,
            )
            result = predictions.to_dict('records')
            
        else:  # Mock mode
            result = self._mock_predict(df)
        
        end_time = datetime.utcnow()
        latency_ms = (end_time - start_time).total_seconds() * 1000
        
        return {
            'predictions': result,
            'model_version': self.version,
            'latency_ms': round(latency_ms, 2),
            'runtime': self._runtime,
        }
    
    async def predict_async(
        self,
        features: Dict[str, Any],
        executor: Optional[ThreadPoolExecutor] = None,
    ) -> Dict[str, Any]:
        """
        Async prediction with thread pool offloading.
        
        This is the correct pattern for FastAPI endpoints.
        Offloads CPU-bound inference to prevent event loop blocking.
        """
        if executor is None:
            executor = get_inference_executor()
        
        loop = asyncio.get_event_loop()
        
        # Offload to thread pool - CRITICAL for non-blocking
        result = await loop.run_in_executor(
            executor,
            self.predict_sync,
            features,
        )
        
        return result
    
    def _mock_predict(self, df) -> List[Dict[str, Any]]:
        """Mock predictions for testing without H2O runtime."""
        import random
        
        results = []
        for _ in range(len(df)):
            p1 = random.random()
            results.append({
                'predict': 1 if p1 > 0.5 else 0,
                'p0': round(1 - p1, 4),
                'p1': round(p1, 4),
            })
        return results
    
    def reload(self, new_path: Optional[str] = None) -> None:
        """
        Hot-reload the model for zero-downtime updates.
        
        Called by the /system/reload-model endpoint.
        """
        if new_path:
            self.model_path = Path(new_path)
        
        print(f"[MOJO] Hot-reloading model: {self.model_path}")
        self._load_model()
    
    def generate_cache_key(self, features: Dict[str, Any]) -> str:
        """
        Generate deterministic cache key for Redis look-aside.
        
        Includes model version for automatic invalidation on deploy.
        """
        # Sort keys for deterministic ordering
        sorted_features = json.dumps(features, sort_keys=True)
        feature_hash = hashlib.sha256(sorted_features.encode()).hexdigest()[:16]
        
        return f"pred:{self.version}:{feature_hash}"


# Global predictor instance - initialized on app startup
_PREDICTOR: Optional[MojoPredictor] = None


def get_predictor() -> MojoPredictor:
    """Get the global predictor instance."""
    if _PREDICTOR is None:
        raise RuntimeError("Predictor not initialized. Call init_predictor() first.")
    return _PREDICTOR


def init_predictor(
    model_path: str,
    genmodel_path: Optional[str] = None,
    version: str = "latest",
) -> MojoPredictor:
    """Initialize the global predictor on app startup."""
    global _PREDICTOR
    _PREDICTOR = MojoPredictor(model_path, genmodel_path, version)
    return _PREDICTOR


if __name__ == '__main__':
    # Test sync prediction
    predictor = MojoPredictor("/tmp/test.mojo")
    result = predictor.predict_sync({'feature_1': 1.5, 'feature_2': 2.3})
    print(json.dumps(result, indent=2))
