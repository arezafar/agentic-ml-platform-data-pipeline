"""
Global Hooks: Pipeline Alerting

Mage Global Hooks for pipeline lifecycle events.
Sends notifications on success, failure, and SLA violations.

Hook Types:
- on_start: Pipeline started
- on_success: Pipeline completed successfully
- on_failure: Pipeline failed
- on_retry: Task retry initiated
"""

from datetime import datetime
from typing import Any, Dict, Optional
import json

# =============================================================================
# Configuration
# =============================================================================

SLACK_WEBHOOK_URL = None  # Set from environment
EMAIL_RECIPIENTS = []
PAGERDUTY_ROUTING_KEY = None


def get_config():
    """Load configuration from environment."""
    from os import environ
    global SLACK_WEBHOOK_URL, EMAIL_RECIPIENTS, PAGERDUTY_ROUTING_KEY
    
    SLACK_WEBHOOK_URL = environ.get('SLACK_WEBHOOK_URL')
    EMAIL_RECIPIENTS = environ.get('EMAIL_RECIPIENTS', '').split(',')
    PAGERDUTY_ROUTING_KEY = environ.get('PAGERDUTY_ROUTING_KEY')


# =============================================================================
# Slack Integration
# =============================================================================

def send_slack_notification(
    webhook_url: str,
    message: str,
    color: str = '#36a64f',
    fields: Optional[list] = None
) -> bool:
    """Send notification to Slack channel."""
    try:
        import httpx
        
        payload = {
            'attachments': [{
                'color': color,
                'text': message,
                'fields': fields or [],
                'footer': 'Agentic ML Platform',
                'ts': datetime.utcnow().timestamp(),
            }]
        }
        
        response = httpx.post(
            webhook_url,
            json=payload,
            timeout=10,
        )
        return response.status_code == 200
        
    except Exception as e:
        print(f"Slack notification failed: {e}")
        return False


# =============================================================================
# Hook Implementations
# =============================================================================

def on_pipeline_start(
    pipeline_uuid: str,
    execution_date: datetime,
    **kwargs
) -> None:
    """Called when pipeline execution starts."""
    get_config()
    
    message = f"🚀 Pipeline `{pipeline_uuid}` started"
    fields = [
        {'title': 'Execution Date', 'value': str(execution_date), 'short': True},
        {'title': 'Status', 'value': 'Running', 'short': True},
    ]
    
    if SLACK_WEBHOOK_URL:
        send_slack_notification(
            SLACK_WEBHOOK_URL,
            message,
            color='#3498db',  # Blue
            fields=fields,
        )


def on_pipeline_success(
    pipeline_uuid: str,
    execution_date: datetime,
    duration_seconds: float,
    metrics: Optional[Dict] = None,
    **kwargs
) -> None:
    """Called when pipeline completes successfully."""
    get_config()
    
    message = f"✅ Pipeline `{pipeline_uuid}` completed successfully"
    fields = [
        {'title': 'Execution Date', 'value': str(execution_date), 'short': True},
        {'title': 'Duration', 'value': f"{duration_seconds:.1f}s", 'short': True},
    ]
    
    # Add model metrics if available
    if metrics:
        for key, value in metrics.items():
            if isinstance(value, float):
                fields.append({'title': key.upper(), 'value': f"{value:.4f}", 'short': True})
    
    if SLACK_WEBHOOK_URL:
        send_slack_notification(
            SLACK_WEBHOOK_URL,
            message,
            color='#2ecc71',  # Green
            fields=fields,
        )


def on_pipeline_failure(
    pipeline_uuid: str,
    execution_date: datetime,
    error_message: str,
    failed_block: Optional[str] = None,
    stack_trace: Optional[str] = None,
    **kwargs
) -> None:
    """Called when pipeline fails."""
    get_config()
    
    message = f"❌ Pipeline `{pipeline_uuid}` FAILED"
    fields = [
        {'title': 'Execution Date', 'value': str(execution_date), 'short': True},
        {'title': 'Failed Block', 'value': failed_block or 'Unknown', 'short': True},
        {'title': 'Error', 'value': error_message[:200], 'short': False},
    ]
    
    if SLACK_WEBHOOK_URL:
        send_slack_notification(
            SLACK_WEBHOOK_URL,
            message,
            color='#e74c3c',  # Red
            fields=fields,
        )
    
    # Trigger PagerDuty for critical pipelines
    if PAGERDUTY_ROUTING_KEY and kwargs.get('is_critical', False):
        trigger_pagerduty(
            routing_key=PAGERDUTY_ROUTING_KEY,
            summary=f"Pipeline {pipeline_uuid} failed: {error_message}",
            severity='error',
        )


def on_sla_miss(
    pipeline_uuid: str,
    execution_date: datetime,
    expected_duration: float,
    actual_duration: float,
    **kwargs
) -> None:
    """Called when pipeline misses SLA."""
    get_config()
    
    message = f"⏰ Pipeline `{pipeline_uuid}` missed SLA"
    fields = [
        {'title': 'Expected', 'value': f"{expected_duration:.0f}s", 'short': True},
        {'title': 'Actual', 'value': f"{actual_duration:.0f}s", 'short': True},
        {'title': 'Overage', 'value': f"{actual_duration - expected_duration:.0f}s", 'short': True},
    ]
    
    if SLACK_WEBHOOK_URL:
        send_slack_notification(
            SLACK_WEBHOOK_URL,
            message,
            color='#f39c12',  # Orange
            fields=fields,
        )


# =============================================================================
# PagerDuty Integration
# =============================================================================

def trigger_pagerduty(
    routing_key: str,
    summary: str,
    severity: str = 'error',
) -> bool:
    """Trigger PagerDuty incident."""
    try:
        import httpx
        
        payload = {
            'routing_key': routing_key,
            'event_action': 'trigger',
            'payload': {
                'summary': summary,
                'severity': severity,
                'source': 'agentic-ml-platform',
            },
        }
        
        response = httpx.post(
            'https://events.pagerduty.com/v2/enqueue',
            json=payload,
            timeout=10,
        )
        return response.status_code == 202
        
    except Exception as e:
        print(f"PagerDuty trigger failed: {e}")
        return False


# =============================================================================
# Mage Hook Registration
# =============================================================================
# These functions are registered as Mage global hooks in pipeline config

PIPELINE_RUN_HOOKS = {
    'on_start': on_pipeline_start,
    'on_success': on_pipeline_success,
    'on_failure': on_pipeline_failure,
    'on_sla_miss': on_sla_miss,
}
