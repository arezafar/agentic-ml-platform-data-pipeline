"""
Job 3: API Inference Pipeline - Request Handler

Mage API Pipeline data loader that accepts HTTP POST requests.
Configured to receive JSON payloads and parse them for inference.

Success Criteria:
- Pipeline accepts HTTP POST requests
- Payload data is accessible via **kwargs or block input
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import json


def load_api_request(*args, **kwargs) -> Dict[str, Any]:
    """
    Data Loader for API inference pipeline.
    
    Accepts JSON payloads from HTTP POST requests and parses
    them into a format suitable for model inference.
    
    Expected payload format:
    {
        "data": [
            {"feature_1": 1.0, "feature_2": 2.0, ...},
            {"feature_1": 3.0, "feature_2": 4.0, ...}
        ],
        "options": {
            "return_probabilities": true,
            "explain": false
        }
    }
    
    Returns:
        Dictionary with parsed request and metadata
    """
    print(f"[API-LOADER] Processing inference request")
    
    # Extract payload from Mage API trigger
    # In Mage, the payload comes via kwargs
    payload = kwargs.get('payload', {})
    
    # If payload is a string, parse it
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError as e:
            return {
                'error': f'Invalid JSON payload: {e}',
                'status': 'error',
            }
    
    # Extract data and options
    input_data = payload.get('data', [])
    options = payload.get('options', {})
    
    # Handle single record vs batch
    if isinstance(input_data, dict):
        input_data = [input_data]
    
    if not input_data:
        return {
            'error': 'No input data provided',
            'status': 'error',
        }
    
    # Validate data has expected features
    # (In production, compare against model's expected features)
    sample_record = input_data[0]
    features = list(sample_record.keys())
    
    print(f"[API-LOADER] Received {len(input_data)} records")
    print(f"[API-LOADER] Features: {features}")
    
    result = {
        'data': input_data,
        'record_count': len(input_data),
        'features': features,
        'options': {
            'return_probabilities': options.get('return_probabilities', True),
            'explain': options.get('explain', False),
            'model_version': options.get('model_version', 'latest'),
        },
        'request_id': kwargs.get('request_id', datetime.utcnow().strftime('%Y%m%d%H%M%S%f')),
        'received_at': datetime.utcnow().isoformat(),
        'status': 'success',
    }
    
    return result


if __name__ == '__main__':
    # Test with mock payload
    mock_payload = {
        'data': [
            {'feature_1': 1.5, 'feature_2': 2.3, 'feature_cat': 'A'},
            {'feature_1': 3.1, 'feature_2': 4.2, 'feature_cat': 'B'},
        ],
        'options': {'return_probabilities': True}
    }
    
    result = load_api_request(payload=mock_payload)
    print(json.dumps(result, indent=2))
