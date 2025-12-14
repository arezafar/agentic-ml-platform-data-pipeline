"""
JTBD Step 3: Prepare - Data Transformation & Feature Engineering

Mage transformer implementing the critical state transition from
Pandas DataFrame to H2O Frame. Includes:
- Data cleaning and standardization
- H2OFrame conversion (Tool Use handoff)
- Word2Vec for text features
- Memory management (h2o.remove_all)

The "Prepare" step refines raw inputs into model-ready features.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import json


def prepare_h2o_frame(data: Dict[str, Any], *args, **kwargs) -> Dict[str, Any]:
    """
    Transform data from Pandas/CSV to H2O Frame format.
    
    This is the critical "Tool Use" handoff where the Mage orchestrator
    transfers data to the H2O compute engine.
    
    Transformations:
    1. Clean column names (lowercase, underscores)
    2. Initialize H2O connection
    3. Clear H2O memory (cleanup)
    4. Convert to H2OFrame
    5. Apply Word2Vec for text columns (if present)
    6. Handle missing values
    
    Args:
        data: Output from load_training_data block
        
    Returns:
        Dictionary with H2OFrame and metadata
    """
    from os import environ
    
    h2o_url = kwargs.get('h2o_url', environ.get('H2O_URL', 'http://h2o-ai:54321'))
    cleanup_on_start = kwargs.get('cleanup_on_start', True)
    target_column = kwargs.get('target_column', 'target')
    
    print(f"[PREPARE] Initializing H2O connection: {h2o_url}")
    
    try:
        import h2o
        import pandas as pd
        
        # Initialize H2O connection
        h2o.init(url=h2o_url)
        
        # CRITICAL: Clean up H2O memory to prevent leaks
        if cleanup_on_start:
            h2o.remove_all()
            print("[PREPARE] H2O memory cleared")
        
        # Load data - prefer direct file import for zero-copy
        if 'csv_path' in data and not data.get('mock'):
            print(f"[PREPARE] Zero-copy import from: {data['csv_path']}")
            hf = h2o.import_file(data['csv_path'])
        elif 'dataframe' in data:
            # Convert from pandas
            df = data['dataframe']
            if isinstance(df, list):
                df = pd.DataFrame(df)
            
            # Clean column names
            df.columns = [c.lower().replace(' ', '_').replace('-', '_') for c in df.columns]
            
            hf = h2o.H2OFrame(df)
        else:
            raise ValueError("No data source provided")
        
        print(f"[PREPARE] H2OFrame created: {hf.nrows} rows, {hf.ncols} columns")
        
        # Detect column types
        numeric_cols = [c for c in hf.columns if hf[c].isnumeric()]
        string_cols = [c for c in hf.columns if hf[c].isstring()]
        
        # Process text columns with Word2Vec if present
        text_columns = kwargs.get('text_columns', [])
        if text_columns:
            hf = _apply_word2vec(hf, text_columns)
        
        # Mark target as categorical for classification
        problem_type = kwargs.get('problem_type', 'classification')
        if problem_type == 'classification' and target_column in hf.columns:
            hf[target_column] = hf[target_column].asfactor()
            print(f"[PREPARE] Target '{target_column}' converted to factor")
        
        # Handle missing values
        for col in hf.columns:
            if hf[col].isna().sum() > 0:
                if hf[col].isnumeric():
                    # Impute with median for numeric
                    median = hf[col].median()
                    hf[col] = hf[col].fillna(median)
                else:
                    # Impute with "MISSING" for categorical
                    hf[col] = hf[col].fillna("MISSING")
        
        result = {
            'h2o_frame': hf,
            'frame_id': hf.frame_id,
            'nrows': hf.nrows,
            'ncols': hf.ncols,
            'columns': hf.columns,
            'numeric_columns': numeric_cols,
            'string_columns': string_cols,
            'target_column': target_column,
            'prepared_at': datetime.utcnow().isoformat(),
        }
        
        print(f"[PREPARE] ✅ H2OFrame ready: {hf.frame_id}")
        return result
        
    except ImportError:
        print("[PREPARE] ⚠️ H2O not available. Returning mock result.")
        return {
            'h2o_frame': None,
            'frame_id': 'mock_frame',
            'nrows': data.get('row_count', 0),
            'ncols': len(data.get('columns', [])),
            'columns': data.get('columns', []),
            'mock': True,
        }


def _apply_word2vec(hf, text_columns: List[str], vec_size: int = 100) -> Any:
    """
    Apply Word2Vec transformation to text columns.
    
    Implements the "Sub-Tool Use" pattern where specialized
    H2O estimators are invoked for feature engineering.
    """
    import h2o
    from h2o.estimators.word2vec import H2OWord2vecEstimator
    
    for col in text_columns:
        if col not in hf.columns:
            continue
        
        print(f"[PREPARE] Applying Word2Vec to column: {col}")
        
        # Tokenize text
        words = hf[col].tokenize("\\W+")
        
        # Train Word2Vec model
        w2v = H2OWord2vecEstimator(
            vec_size=vec_size,
            model_id=f"w2v_{col}",
            epochs=10,
            min_word_freq=3,
        )
        w2v.train(training_frame=words)
        
        # Transform to vectors (average method)
        vectors = w2v.transform(words, aggregate_method="AVERAGE")
        
        # Rename vector columns
        for i, c in enumerate(vectors.columns):
            vectors[c].set_name(f"{col}_vec_{i}")
        
        # Bind to main frame and drop original text column
        hf = hf.cbind(vectors)
        hf = hf.drop(col)
        
        print(f"[PREPARE] Word2Vec added {vec_size} features for '{col}'")
    
    return hf


if __name__ == '__main__':
    # Test with mock data
    mock_input = {
        'dataframe': [
            {'feature_1': 1.0, 'feature_2': 2.0, 'target': 1},
            {'feature_1': 3.0, 'feature_2': 4.0, 'target': 0},
        ],
        'row_count': 2,
        'columns': ['feature_1', 'feature_2', 'target'],
    }
    result = prepare_h2o_frame(mock_input)
    print(json.dumps({k: v for k, v in result.items() if k != 'h2o_frame'}, indent=2))
