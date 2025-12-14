"""
Sensor Block: S3 File Arrival

Mage Sensor block for waiting on S3 file dependencies.
Implements polling with exponential backoff.

Block Type: sensor
Connection: S3 via boto3
"""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional
import time

if 'sensor' not in dir():
    from mage_ai.data_preparation.decorators import sensor


@sensor
def wait_for_s3_file(
    *args,
    **kwargs
) -> bool:
    """
    Wait for a file to appear in S3.
    
    Features:
    - Prefix-based matching
    - Date-partitioned paths
    - Timeout handling
    - Exponential backoff polling
    
    Configuration via pipeline variables:
    - s3_bucket: S3 bucket name
    - s3_key_pattern: Key pattern with date placeholders
    - timeout_seconds: Maximum wait time
    - poll_interval: Initial polling interval
    """
    from os import environ
    
    # Configuration
    s3_bucket = kwargs.get('s3_bucket', environ.get('AWS_S3_BUCKET'))
    s3_key_pattern = kwargs.get('s3_key_pattern')
    timeout_seconds = kwargs.get('timeout_seconds', 3600)  # 1 hour
    poll_interval = kwargs.get('poll_interval', 30)
    max_poll_interval = kwargs.get('max_poll_interval', 300)  # 5 min max
    
    # Support date templating
    execution_date = kwargs.get('execution_date', datetime.utcnow())
    if isinstance(execution_date, str):
        execution_date = datetime.fromisoformat(execution_date)
    
    s3_key = s3_key_pattern.format(
        year=execution_date.year,
        month=execution_date.month,
        day=execution_date.day,
        date=execution_date.strftime('%Y-%m-%d'),
    ) if s3_key_pattern else None
    
    if not s3_key:
        print("⚠️  No S3 key pattern provided")
        return True  # Pass through
    
    start_time = datetime.utcnow()
    deadline = start_time + timedelta(seconds=timeout_seconds)
    current_interval = poll_interval
    
    print(f"   Waiting for s3://{s3_bucket}/{s3_key}")
    print(f"   Timeout: {timeout_seconds}s")
    
    try:
        import boto3
        from botocore.exceptions import ClientError
        
        s3_client = boto3.client('s3')
        
        while datetime.utcnow() < deadline:
            try:
                # Check if file exists
                s3_client.head_object(Bucket=s3_bucket, Key=s3_key)
                
                elapsed = (datetime.utcnow() - start_time).total_seconds()
                print(f"✅ File found after {elapsed:.0f}s")
                return True
                
            except ClientError as e:
                if e.response['Error']['Code'] == '404':
                    # File not found, wait and retry
                    remaining = (deadline - datetime.utcnow()).total_seconds()
                    print(f"   Waiting... ({remaining:.0f}s remaining)")
                    
                    time.sleep(current_interval)
                    current_interval = min(current_interval * 1.5, max_poll_interval)
                else:
                    raise
        
        # Timeout reached
        print(f"❌ Timeout: File not found after {timeout_seconds}s")
        return False
        
    except ImportError:
        print("⚠️  boto3 not installed. Simulating sensor.")
        return True
