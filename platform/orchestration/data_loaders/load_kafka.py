"""
Data Loader: Kafka Streaming Source

Mage Data Loader block for consuming messages from Apache Kafka.
Supports both batch and streaming contexts.

Block Type: data_loader
Connection: Kafka via confluent-kafka

Usage in pipeline:
    @data_loader
    def load_kafka_stream(**kwargs):
        ...
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
import json
import pandas as pd

if 'data_loader' not in dir():
    from mage_ai.data_preparation.decorators import data_loader
if 'test' not in dir():
    from mage_ai.data_preparation.decorators import test


@data_loader
def load_from_kafka(
    *args,
    **kwargs
) -> pd.DataFrame:
    """
    Consume messages from Kafka topic.
    
    Features:
    - Batch consumption with timeout
    - JSON message deserialization
    - Offset management
    - Dead letter queue support
    
    Configuration via pipeline variables:
    - topic: Kafka topic to consume from
    - consumer_group: Consumer group ID
    - batch_size: Max messages per batch
    - timeout_seconds: Max time to wait for messages
    """
    from os import environ
    
    # Configuration
    bootstrap_servers = kwargs.get(
        'bootstrap_servers', 
        environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
    )
    topic = kwargs.get('topic', 'raw_events')
    consumer_group = kwargs.get(
        'consumer_group', 
        environ.get('KAFKA_CONSUMER_GROUP', 'mage-pipeline')
    )
    batch_size = kwargs.get('batch_size', 1000)
    timeout_seconds = kwargs.get('timeout_seconds', 30)
    auto_offset_reset = kwargs.get('auto_offset_reset', 'earliest')
    
    messages = []
    errors = []
    
    try:
        from confluent_kafka import Consumer, KafkaError, KafkaException
        
        # Consumer configuration
        conf = {
            'bootstrap.servers': bootstrap_servers,
            'group.id': consumer_group,
            'auto.offset.reset': auto_offset_reset,
            'enable.auto.commit': False,  # Manual commit for exactly-once
        }
        
        consumer = Consumer(conf)
        consumer.subscribe([topic])
        
        print(f"   Consuming from topic: {topic}")
        
        # Consume messages
        end_time = datetime.utcnow().timestamp() + timeout_seconds
        
        while len(messages) < batch_size and datetime.utcnow().timestamp() < end_time:
            msg = consumer.poll(timeout=1.0)
            
            if msg is None:
                continue
            
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    print(f"   Reached end of partition")
                    break
                else:
                    errors.append({
                        'error': str(msg.error()),
                        'partition': msg.partition(),
                        'offset': msg.offset(),
                    })
                    continue
            
            try:
                # Deserialize JSON message
                value = json.loads(msg.value().decode('utf-8'))
                
                # Add Kafka metadata
                value['_kafka_topic'] = msg.topic()
                value['_kafka_partition'] = msg.partition()
                value['_kafka_offset'] = msg.offset()
                value['_kafka_timestamp'] = msg.timestamp()[1]
                value['_loaded_at'] = datetime.utcnow().isoformat()
                
                messages.append(value)
                
            except json.JSONDecodeError as e:
                errors.append({
                    'error': f'JSON decode error: {e}',
                    'partition': msg.partition(),
                    'offset': msg.offset(),
                    'raw_value': msg.value().decode('utf-8')[:100],
                })
        
        # Commit offsets after successful processing
        consumer.commit()
        consumer.close()
        
    except ImportError:
        print("⚠️  confluent-kafka not installed. Using mock data for development.")
        # Mock data for development without Kafka
        messages = [
            {
                'id': i,
                'event_type': 'mock_event',
                'payload': {'value': i * 10},
                '_kafka_topic': topic,
                '_kafka_partition': 0,
                '_kafka_offset': i,
                '_kafka_timestamp': datetime.utcnow().timestamp(),
                '_loaded_at': datetime.utcnow().isoformat(),
            }
            for i in range(10)
        ]
    
    # Convert to DataFrame
    df = pd.DataFrame(messages)
    
    print(f"✅ Consumed {len(messages)} messages from Kafka")
    if errors:
        print(f"⚠️  {len(errors)} errors encountered (see logs)")
        # Store errors for dead letter queue processing
        kwargs['runtime_storage'] = {'kafka_errors': errors}
    
    return df


@test
def test_output(output: pd.DataFrame, *args) -> None:
    """Test that output is valid."""
    assert output is not None, 'Output is undefined'
    assert isinstance(output, pd.DataFrame), 'Output must be a DataFrame'
    print(f"✓ Output validation passed: {len(output)} rows")


@test
def test_kafka_metadata(output: pd.DataFrame, *args) -> None:
    """Test for Kafka metadata columns."""
    if len(output) > 0:
        expected = ['_kafka_topic', '_kafka_partition', '_kafka_offset']
        for col in expected:
            assert col in output.columns, f'Missing {col} column'
        print(f"✓ Kafka metadata columns present")
