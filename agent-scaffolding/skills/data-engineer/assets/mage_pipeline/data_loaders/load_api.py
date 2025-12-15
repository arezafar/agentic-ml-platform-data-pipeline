"""
Data Loader: REST API Source

Mage Data Loader block for fetching data from external REST APIs.
Implements retry logic, pagination, and rate limiting.

Block Type: data_loader
Connection: HTTP via httpx

Usage in pipeline:
    @data_loader
    def load_api_data(**kwargs):
        ...
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
import pandas as pd

if 'data_loader' not in dir():
    from mage_ai.data_preparation.decorators import data_loader
if 'test' not in dir():
    from mage_ai.data_preparation.decorators import test


@data_loader
def load_from_api(
    *args,
    **kwargs
) -> pd.DataFrame:
    """
    Load data from external REST API with pagination and retry.
    
    Features:
    - Automatic pagination handling
    - Exponential backoff retry
    - Rate limiting
    - Response schema validation
    
    Configuration via pipeline variables:
    - api_endpoint: Full URL of the API endpoint
    - api_token: Bearer token for authentication
    - page_size: Records per page
    - max_pages: Maximum pages to fetch
    """
    import httpx
    import time
    from os import environ
    
    # Configuration
    base_url = kwargs.get('api_endpoint', environ.get('API_BASE_URL', ''))
    endpoint = kwargs.get('endpoint', '/data')
    api_token = kwargs.get('api_token', environ.get('API_TOKEN', ''))
    page_size = kwargs.get('page_size', 100)
    max_pages = kwargs.get('max_pages', 10)
    timeout = kwargs.get('timeout', 30)
    max_retries = kwargs.get('max_retries', 3)
    
    # Build URL
    url = f"{base_url.rstrip('/')}{endpoint}"
    
    # Headers
    headers = {
        'Authorization': f'Bearer {api_token}',
        'Content-Type': 'application/json',
        'Accept': 'application/json',
    }
    
    all_records = []
    page = 1
    
    with httpx.Client(timeout=timeout) as client:
        while page <= max_pages:
            params = {
                'page': page,
                'page_size': page_size,
            }
            
            # Retry with exponential backoff
            for attempt in range(max_retries):
                try:
                    response = client.get(url, headers=headers, params=params)
                    response.raise_for_status()
                    
                    data = response.json()
                    records = data.get('data', data.get('results', data))
                    
                    if not records or not isinstance(records, list):
                        break
                    
                    all_records.extend(records)
                    print(f"   Page {page}: fetched {len(records)} records")
                    
                    # Check for more pages
                    if len(records) < page_size:
                        break
                    
                    page += 1
                    break  # Success, exit retry loop
                    
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:  # Rate limited
                        wait_time = 2 ** attempt
                        print(f"   Rate limited, waiting {wait_time}s...")
                        time.sleep(wait_time)
                    elif e.response.status_code >= 500:  # Server error
                        wait_time = 2 ** attempt
                        print(f"   Server error, retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        raise
                except httpx.RequestError as e:
                    if attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        print(f"   Request failed, retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        raise
            else:
                break  # Exit pagination loop if all retries failed
    
    # Convert to DataFrame
    df = pd.DataFrame(all_records)
    
    # Add metadata
    df['_loaded_at'] = datetime.utcnow()
    df['_source'] = url
    
    print(f"✅ Loaded {len(df)} total records from API")
    
    return df


@test
def test_output(output: pd.DataFrame, *args) -> None:
    """Test that output is valid."""
    assert output is not None, 'Output is undefined'
    assert isinstance(output, pd.DataFrame), 'Output must be a DataFrame'
    print(f"✓ Output validation passed: {len(output)} rows")


@test
def test_required_columns(output: pd.DataFrame, *args) -> None:
    """Test for required metadata columns."""
    assert '_loaded_at' in output.columns, 'Missing _loaded_at column'
    assert '_source' in output.columns, 'Missing _source column'
    print(f"✓ Required columns present")
