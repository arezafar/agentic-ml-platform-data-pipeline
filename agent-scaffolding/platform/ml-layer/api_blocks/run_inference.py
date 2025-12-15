"""
Job 3: Real-time Inference Block

Custom block that loads H2O MOJO and performs predictions.
Uses h2o.mojo_predict_pandas or model.predict() to score incoming data.

Success Criteria:
- API returns valid JSON predictions
- Latency is within acceptable limits
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


def run_inference(request_data: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
    """
    Execute real-time inference using H2O MOJO.
    
    Loads the production MOJO model and scores incoming data.
    Handles data type conversions to match H2O training schema.
    
    Args:
        request_data: Output from load_api_request block
        
    Returns:
        JSON dictionary with predictions
    """
    from os import environ
    
    if request_data.get('status') == 'error':
        return request_data  # Pass through error
    
    model_path = kwargs.get('model_path', environ.get('MODEL_PATH', '/models/production/model.mojo'))
    genmodel_path = kwargs.get('genmodel_path', environ.get('GENMODEL_JAR', '/models/production/h2o-genmodel.jar'))
    
    print(f"[INFERENCE] Loading model: {model_path}")
    
    start_time = datetime.utcnow()
    
    # Extract input data
    input_data = request_data.get('data', [])
    options = request_data.get('options', {})
    
    try:
        import pandas as pd
        import h2o
        
        # Convert input to DataFrame
        df = pd.DataFrame(input_data)
        
        # Clean column names to match training
        df.columns = [c.lower().replace(' ', '_').replace('-', '_') for c in df.columns]
        
        print(f"[INFERENCE] Scoring {len(df)} records...")
        
        # Method 1: Use MOJO directly (preferred for production)
        if Path(model_path).exists():
            predictions = h2o.mojo_predict_pandas(
                dataframe=df,
                mojo_zip_path=model_path,
                genmodel_jar_path=genmodel_path if Path(genmodel_path).exists() else None,
            )
        else:
            # Method 2: Use in-memory model (fallback)
            # This requires the model to be loaded in H2O cluster
            h2o.init(url=environ.get('H2O_URL', 'http://h2o-ai:54321'))
            hf = h2o.H2OFrame(df)
            
            # Load model from registry (would need model_id)
            model_id = kwargs.get('model_id')
            if model_id:
                model = h2o.get_model(model_id)
                predictions = model.predict(hf).as_data_frame()
            else:
                raise ValueError("No MOJO path or model_id provided")
        
        end_time = datetime.utcnow()
        latency_ms = (end_time - start_time).total_seconds() * 1000
        
        # Format response
        response = _format_predictions(
            predictions,
            options=options,
            latency_ms=latency_ms,
            request_id=request_data.get('request_id'),
        )
        
        print(f"[INFERENCE] ✅ Completed in {latency_ms:.1f}ms")
        
        return response
        
    except ImportError:
        print("[INFERENCE] ⚠️ H2O not available. Returning mock predictions.")
        return _mock_predictions(input_data, request_data.get('request_id'))
        
    except Exception as e:
        print(f"[INFERENCE] ❌ Error: {e}")
        return {
            'status': 'error',
            'error': str(e),
            'request_id': request_data.get('request_id'),
        }


def _format_predictions(
    predictions,
    options: Dict,
    latency_ms: float,
    request_id: str,
) -> Dict[str, Any]:
    """Format predictions for API response."""
    import pandas as pd
    
    if isinstance(predictions, pd.DataFrame):
        predictions = predictions.to_dict('records')
    
    response = {
        'status': 'success',
        'request_id': request_id,
        'predictions': [],
        'metadata': {
            'latency_ms': round(latency_ms, 2),
            'model_version': options.get('model_version', 'latest'),
            'timestamp': datetime.utcnow().isoformat(),
        },
    }
    
    return_probabilities = options.get('return_probabilities', True)
    
    for pred in predictions:
        if return_probabilities and 'p0' in pred and 'p1' in pred:
            response['predictions'].append({
                'class': int(pred.get('predict', 0)),
                'probabilities': {
                    'class_0': float(pred.get('p0', 0)),
                    'class_1': float(pred.get('p1', 0)),
                },
            })
        elif 'predict' in pred:
            response['predictions'].append({
                'value': pred['predict'],
            })
        else:
            response['predictions'].append(pred)
    
    return response


def _mock_predictions(input_data: List[Dict], request_id: str) -> Dict[str, Any]:
    """Return mock predictions for testing."""
    import random
    
    predictions = []
    for _ in input_data:
        p1 = random.random()
        predictions.append({
            'class': 1 if p1 > 0.5 else 0,
            'probabilities': {
                'class_0': round(1 - p1, 4),
                'class_1': round(p1, 4),
            },
        })
    
    return {
        'status': 'success',
        'request_id': request_id,
        'predictions': predictions,
        'metadata': {
            'latency_ms': 5.0,
            'model_version': 'mock',
            'mock': True,
        },
    }


if __name__ == '__main__':
    # Test with mock request
    mock_request = {
        'data': [
            {'feature_1': 1.5, 'feature_2': 2.3},
            {'feature_1': 3.1, 'feature_2': 4.2},
        ],
        'options': {'return_probabilities': True},
        'request_id': 'test_123',
        'status': 'success',
    }
    
    result = run_inference(mock_request)
    print(json.dumps(result, indent=2))
