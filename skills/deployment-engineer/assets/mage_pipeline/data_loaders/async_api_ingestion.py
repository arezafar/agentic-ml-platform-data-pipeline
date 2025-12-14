"""
Async API Ingestion Data Loader (Mage Block)
=============================================================================
PROC-01-01: Async Data Loader using httpx + asyncio

This block demonstrates the correct pattern for high-throughput API ingestion
in Mage pipelines without blocking the event loop.

Key Patterns:
- Uses `async def` signature for non-blocking I/O
- httpx.AsyncClient for concurrent HTTP requests
- Semaphore for rate limiting / connection pooling
- Proper error handling with retries

Usage:
    1. Copy to your Mage project's data_loaders/ directory
    2. Configure API_BASE_URL and authentication
    3. Connect to transformer blocks for feature engineering
=============================================================================
"""

import asyncio
from typing import Any
import pandas as pd

# Conditional imports for standalone testing
if __name__ != "__main__":
    from mage_ai.data_preparation.decorators import data_loader
    from mage_ai.data_preparation.shared.secrets import get_secret_value
else:
    def data_loader(func):
        return func
    def get_secret_value(key):
        return "test-token"

import httpx


# Configuration
API_BASE_URL = "https://api.example.com/v1"
MAX_CONCURRENT_REQUESTS = 10
REQUEST_TIMEOUT = 30.0
MAX_RETRIES = 3


@data_loader
async def load_data_from_api(*args, **kwargs) -> pd.DataFrame:
    """
    Async data loader that fetches data from an external API.
    
    PROC-01-01: Uses async def signature to allow concurrent I/O operations.
    The Mage executor will properly await this coroutine.
    
    Returns:
        pd.DataFrame: Ingested data from API
    """
    # Get API token from secrets manager
    api_token = get_secret_value("API_TOKEN")
    
    # Configure endpoints to fetch
    endpoints = [
        "/entities",
        "/transactions",
        "/events",
    ]
    
    # Semaphore for rate limiting
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)
    
    async def fetch_with_retry(
        client: httpx.AsyncClient, 
        endpoint: str
    ) -> dict[str, Any]:
        """Fetch single endpoint with retry logic."""
        async with semaphore:
            for attempt in range(MAX_RETRIES):
                try:
                    response = await client.get(
                        f"{API_BASE_URL}{endpoint}",
                        timeout=REQUEST_TIMEOUT,
                    )
                    response.raise_for_status()
                    return {"endpoint": endpoint, "data": response.json()}
                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429:  # Rate limited
                        wait_time = 2 ** attempt
                        await asyncio.sleep(wait_time)
                    elif e.response.status_code >= 500:  # Server error
                        await asyncio.sleep(1)
                    else:
                        raise
                except httpx.TimeoutException:
                    if attempt == MAX_RETRIES - 1:
                        raise
                    await asyncio.sleep(1)
            return {"endpoint": endpoint, "data": None, "error": "Max retries exceeded"}
    
    # Execute requests concurrently
    async with httpx.AsyncClient(
        headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }
    ) as client:
        tasks = [fetch_with_retry(client, ep) for ep in endpoints]
        results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Process results into DataFrame
    all_records = []
    for result in results:
        if isinstance(result, Exception):
            print(f"Request failed: {result}")
            continue
        if result.get("data"):
            records = result["data"]
            if isinstance(records, list):
                for record in records:
                    record["_source_endpoint"] = result["endpoint"]
                    all_records.append(record)
            else:
                records["_source_endpoint"] = result["endpoint"]
                all_records.append(records)
    
    df = pd.DataFrame(all_records)
    print(f"Loaded {len(df)} records from {len(endpoints)} endpoints")
    
    return df


@data_loader
async def load_paginated_api(*args, **kwargs) -> pd.DataFrame:
    """
    Alternative: Paginated API loader with cursor-based pagination.
    
    Use this pattern for APIs that return large datasets in pages.
    """
    api_token = get_secret_value("API_TOKEN")
    all_records = []
    cursor = None
    page_size = 100
    
    async with httpx.AsyncClient(
        headers={"Authorization": f"Bearer {api_token}"}
    ) as client:
        while True:
            params = {"limit": page_size}
            if cursor:
                params["cursor"] = cursor
            
            response = await client.get(
                f"{API_BASE_URL}/entities",
                params=params,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            
            all_records.extend(data.get("items", []))
            cursor = data.get("next_cursor")
            
            if not cursor or len(data.get("items", [])) < page_size:
                break
    
    return pd.DataFrame(all_records)


# Test harness
if __name__ == "__main__":
    async def test():
        result = await load_data_from_api()
        print(f"Result shape: {result.shape if hasattr(result, 'shape') else 'empty'}")
    
    asyncio.run(test())
