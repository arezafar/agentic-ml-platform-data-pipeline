"""
Airflow DAG Template

Production-ready boilerplate for Agentic ML Platform including:
- Retry logic with exponential backoff
- SLA monitoring and alerting
- Structured logging
- Dynamic task generation
- Integration patterns for Mage and H2O

Usage:
    Copy and customize for new pipeline requirements.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from airflow import DAG
from airflow.operators.python import PythonOperator, BranchPythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.sensors.external_task import ExternalTaskSensor
from airflow.utils.trigger_rule import TriggerRule

import logging
import json

# =============================================================================
# CONFIGURATION
# =============================================================================

DAG_ID = "{{ dag_id }}"
DAG_DESCRIPTION = "{{ dag_description }}"
OWNER = "{{ owner }}"
SCHEDULE_INTERVAL = "@daily"  # Options: @hourly, @daily, @weekly, cron expression, or None

# SLA Configuration
SLA_MISS_CALLBACK = None  # Replace with your alerting function

# Default arguments for all tasks
default_args = {
    'owner': OWNER,
    'depends_on_past': False,
    'email': ['{{ alert_email }}'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'retry_exponential_backoff': True,
    'max_retry_delay': timedelta(hours=1),
    'execution_timeout': timedelta(hours=2),
    'sla': timedelta(hours=4),
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_logger(task_name: str) -> logging.Logger:
    """Get structured logger for a task."""
    logger = logging.getLogger(f"airflow.task.{DAG_ID}.{task_name}")
    return logger


def on_failure_callback(context: Dict[str, Any]) -> None:
    """Callback executed on task failure.
    
    Use this for:
    - Sending alerts to Slack/PagerDuty
    - Writing to incident management systems
    - Triggering automated remediation
    """
    task_instance = context.get('task_instance')
    exception = context.get('exception')
    
    logger = get_logger('failure_callback')
    logger.error(
        f"Task {task_instance.task_id} failed",
        extra={
            'dag_id': DAG_ID,
            'task_id': task_instance.task_id,
            'execution_date': str(context.get('execution_date')),
            'exception': str(exception),
            'try_number': task_instance.try_number,
        }
    )
    
    # TODO: Integrate with your alerting system
    # slack_alert(f"Task {task_instance.task_id} failed: {exception}")


def on_success_callback(context: Dict[str, Any]) -> None:
    """Callback executed on task success."""
    task_instance = context.get('task_instance')
    logger = get_logger('success_callback')
    
    logger.info(
        f"Task {task_instance.task_id} succeeded",
        extra={
            'dag_id': DAG_ID,
            'task_id': task_instance.task_id,
            'execution_date': str(context.get('execution_date')),
            'duration': task_instance.duration,
        }
    )


# =============================================================================
# TASK FUNCTIONS
# =============================================================================

def extract_data(**context) -> Dict[str, Any]:
    """Extract data from source system.
    
    Implements:
    - Connection pooling
    - Retry with backoff
    - Schema validation
    """
    logger = get_logger('extract_data')
    execution_date = context['execution_date']
    
    logger.info(f"Extracting data for {execution_date}")
    
    # TODO: Implement extraction logic
    # Example: Call Mage API to trigger pipeline
    # response = requests.post(
    #     "http://mage-service:6789/api/pipeline_schedules/1/trigger",
    #     json={"variables": {"date": str(execution_date)}}
    # )
    
    extracted_records = 0  # Replace with actual count
    
    # Push to XCom for downstream tasks
    context['ti'].xcom_push(key='record_count', value=extracted_records)
    
    return {'status': 'success', 'records': extracted_records}


def validate_data(**context) -> str:
    """Validate extracted data using H2O profiling.
    
    Returns:
        Branch task ID: 'transform_data' or 'quarantine_data'
    """
    logger = get_logger('validate_data')
    record_count = context['ti'].xcom_pull(key='record_count', task_ids='extract_data')
    
    logger.info(f"Validating {record_count} records")
    
    # TODO: Implement H2O-based validation
    # Example: Check for anomalies using Isolation Forest
    # anomaly_score = h2o_client.score_batch(data)
    
    is_valid = True  # Replace with actual validation
    
    if is_valid:
        logger.info("Data validation passed")
        return 'transform_data'
    else:
        logger.warning("Data validation failed - routing to quarantine")
        return 'quarantine_data'


def transform_data(**context) -> Dict[str, Any]:
    """Transform data using dbt or H2O.
    
    Implements:
    - Idempotent transformations
    - Lineage tracking
    - Feature engineering
    """
    logger = get_logger('transform_data')
    
    # TODO: Implement transformation logic
    # Example: Trigger dbt run
    # subprocess.run(['dbt', 'run', '--select', 'my_model'])
    
    transformed_records = 0
    
    return {'status': 'success', 'records': transformed_records}


def quarantine_data(**context) -> Dict[str, Any]:
    """Handle invalid data by quarantining.
    
    Routes problematic data to review queue instead of failing pipeline.
    """
    logger = get_logger('quarantine_data')
    
    logger.warning("Moving data to quarantine table")
    
    # TODO: Implement quarantine logic
    # INSERT INTO quarantine.failed_batches SELECT * FROM staging.batch
    
    return {'status': 'quarantined'}


def load_data(**context) -> Dict[str, Any]:
    """Load transformed data to destination.
    
    Implements:
    - Upsert logic
    - Transaction management
    - Post-load validation
    """
    logger = get_logger('load_data')
    
    # TODO: Implement loading logic
    
    return {'status': 'success'}


def send_notification(**context) -> None:
    """Send pipeline completion notification."""
    logger = get_logger('send_notification')
    
    stats = {
        'dag_id': DAG_ID,
        'execution_date': str(context['execution_date']),
        'status': 'completed',
    }
    
    logger.info(f"Pipeline completed: {json.dumps(stats)}")


# =============================================================================
# DAG DEFINITION
# =============================================================================

with DAG(
    dag_id=DAG_ID,
    description=DAG_DESCRIPTION,
    default_args=default_args,
    schedule_interval=SCHEDULE_INTERVAL,
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['agentic', 'ml-platform', '{{ tag }}'],
    max_active_runs=1,
    on_failure_callback=on_failure_callback,
    sla_miss_callback=SLA_MISS_CALLBACK,
) as dag:
    
    # Start marker
    start = EmptyOperator(
        task_id='start',
    )
    
    # Wait for upstream dependency (optional)
    wait_for_upstream = ExternalTaskSensor(
        task_id='wait_for_upstream',
        external_dag_id='upstream_dag',
        external_task_id='end',
        allowed_states=['success'],
        failed_states=['failed', 'skipped'],
        mode='reschedule',
        poke_interval=300,
        timeout=3600,
        soft_fail=True,  # Don't fail DAG if upstream missing
    )
    
    # Extract
    extract = PythonOperator(
        task_id='extract_data',
        python_callable=extract_data,
        on_success_callback=on_success_callback,
    )
    
    # Validate (branching)
    validate = BranchPythonOperator(
        task_id='validate_data',
        python_callable=validate_data,
    )
    
    # Transform (happy path)
    transform = PythonOperator(
        task_id='transform_data',
        python_callable=transform_data,
    )
    
    # Quarantine (sad path)
    quarantine = PythonOperator(
        task_id='quarantine_data',
        python_callable=quarantine_data,
    )
    
    # Load
    load = PythonOperator(
        task_id='load_data',
        python_callable=load_data,
        trigger_rule=TriggerRule.NONE_FAILED_MIN_ONE_SUCCESS,
    )
    
    # Notify
    notify = PythonOperator(
        task_id='send_notification',
        python_callable=send_notification,
        trigger_rule=TriggerRule.ALL_DONE,
    )
    
    # End marker
    end = EmptyOperator(
        task_id='end',
        trigger_rule=TriggerRule.ALL_DONE,
    )
    
    # Define dependencies
    start >> wait_for_upstream >> extract >> validate
    validate >> [transform, quarantine]
    transform >> load
    quarantine >> load
    load >> notify >> end


# =============================================================================
# DYNAMIC TASK GENERATION (Optional Pattern)
# =============================================================================
# 
# For generating tasks dynamically based on configuration:
#
# def create_processing_tasks(config: List[Dict]) -> List[PythonOperator]:
#     tasks = []
#     for item in config:
#         task = PythonOperator(
#             task_id=f"process_{item['name']}",
#             python_callable=process_item,
#             op_kwargs={'item': item},
#         )
#         tasks.append(task)
#     return tasks
