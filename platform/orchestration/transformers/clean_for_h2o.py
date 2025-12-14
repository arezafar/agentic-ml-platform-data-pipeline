"""
Transformer: Clean and Prepare Data for H2O

Mage Transformer block for data cleaning and feature engineering.
Prepares data specifically for H2O consumption.

Block Type: transformer
Processing: Pandas/Polars
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd

if 'transformer' not in dir():
    from mage_ai.data_preparation.decorators import transformer
if 'test' not in dir():
    from mage_ai.data_preparation.decorators import test


@transformer
def clean_and_prepare(
    data: pd.DataFrame,
    *args,
    **kwargs
) -> pd.DataFrame:
    """
    Clean and transform data for H2O consumption.
    
    Features:
    - NULL handling strategies
    - Type conversion for H2O compatibility
    - Timestamp normalization
    - Categorical encoding preparation
    - Feature engineering
    
    H2O Type Requirements:
    - Categorical strings → H2O will auto-detect as enum
    - Numeric columns → H2O prefers float64
    - Dates → H2O parses ISO format strings
    """
    if data is None or len(data) == 0:
        return pd.DataFrame()
    
    df = data.copy()
    print(f"   Input: {len(df)} rows, {len(df.columns)} columns")
    
    # Track cleaning operations
    operations = []
    
    # -------------------------------------------------------------------------
    # Step 1: Handle NULLs
    # -------------------------------------------------------------------------
    null_strategy = kwargs.get('null_strategy', 'median')
    null_threshold = kwargs.get('null_threshold', 0.5)  # Drop columns with >50% nulls
    
    # Drop columns with too many nulls
    null_ratios = df.isnull().mean()
    cols_to_drop = null_ratios[null_ratios > null_threshold].index.tolist()
    if cols_to_drop:
        df = df.drop(columns=cols_to_drop)
        operations.append(f"Dropped {len(cols_to_drop)} high-null columns")
    
    # Fill remaining nulls
    numeric_cols = df.select_dtypes(include=['int64', 'float64']).columns
    categorical_cols = df.select_dtypes(include=['object', 'category']).columns
    
    for col in numeric_cols:
        if df[col].isnull().any():
            if null_strategy == 'median':
                fill_value = df[col].median()
            elif null_strategy == 'mean':
                fill_value = df[col].mean()
            else:
                fill_value = 0
            df[col] = df[col].fillna(fill_value)
    
    for col in categorical_cols:
        if df[col].isnull().any():
            df[col] = df[col].fillna('MISSING')
    
    operations.append(f"Filled nulls using {null_strategy} strategy")
    
    # -------------------------------------------------------------------------
    # Step 2: Normalize Timestamps
    # -------------------------------------------------------------------------
    datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
    
    # Also detect string columns that look like dates
    for col in categorical_cols:
        sample = df[col].dropna().head(100)
        if len(sample) > 0:
            try:
                pd.to_datetime(sample, errors='raise')
                datetime_cols.append(col)
            except:
                pass
    
    for col in datetime_cols:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
            # Convert to ISO format string for H2O
            df[f'{col}_str'] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S')
            # Extract useful features
            df[f'{col}_year'] = df[col].dt.year
            df[f'{col}_month'] = df[col].dt.month
            df[f'{col}_day'] = df[col].dt.day
            df[f'{col}_hour'] = df[col].dt.hour
            df[f'{col}_dayofweek'] = df[col].dt.dayofweek
    
    if datetime_cols:
        operations.append(f"Processed {len(datetime_cols)} datetime columns")
    
    # -------------------------------------------------------------------------
    # Step 3: Type Conversion for H2O
    # -------------------------------------------------------------------------
    # H2O prefers explicit types
    for col in df.select_dtypes(include=['int64']).columns:
        df[col] = df[col].astype('float64')
    
    # Convert boolean to int for H2O
    for col in df.select_dtypes(include=['bool']).columns:
        df[col] = df[col].astype('int64')
    
    operations.append("Converted types for H2O compatibility")
    
    # -------------------------------------------------------------------------
    # Step 4: Feature Engineering (Basic)
    # -------------------------------------------------------------------------
    feature_config = kwargs.get('features', [])
    
    for feature in feature_config:
        if feature.get('type') == 'interaction':
            col1, col2 = feature['columns']
            if col1 in df.columns and col2 in df.columns:
                df[f'{col1}_x_{col2}'] = df[col1] * df[col2]
        
        elif feature.get('type') == 'ratio':
            col1, col2 = feature['columns']
            if col1 in df.columns and col2 in df.columns:
                df[f'{col1}_div_{col2}'] = df[col1] / df[col2].replace(0, 1)
        
        elif feature.get('type') == 'log':
            col = feature['column']
            if col in df.columns:
                df[f'{col}_log'] = df[col].apply(lambda x: max(x, 0.001)).apply(pd.np.log)
    
    # -------------------------------------------------------------------------
    # Step 5: Add Metadata
    # -------------------------------------------------------------------------
    df['_transformed_at'] = datetime.utcnow().isoformat()
    
    # Log operations
    print(f"   Transformations applied:")
    for op in operations:
        print(f"     - {op}")
    print(f"✅ Output: {len(df)} rows, {len(df.columns)} columns")
    
    return df


@test
def test_no_nulls(output: pd.DataFrame, *args) -> None:
    """Test that numeric columns have no nulls."""
    numeric_cols = output.select_dtypes(include=['float64', 'int64']).columns
    for col in numeric_cols:
        null_count = output[col].isnull().sum()
        assert null_count == 0, f'Column {col} has {null_count} nulls'
    print(f"✓ No nulls in numeric columns")


@test
def test_h2o_types(output: pd.DataFrame, *args) -> None:
    """Test that types are H2O-compatible."""
    for col in output.columns:
        dtype = output[col].dtype
        valid_types = ['float64', 'int64', 'object', 'category', 'datetime64[ns]']
        assert any(str(dtype).startswith(t.split('[')[0]) for t in valid_types), \
            f'Column {col} has incompatible type: {dtype}'
    print(f"✓ All columns have H2O-compatible types")
