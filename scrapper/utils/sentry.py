"""Sentry initialization and configuration."""

import logging
import os
from typing import Dict, Any, Optional
from functools import wraps

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.threading import ThreadingIntegration

logger = logging.getLogger(__name__)

def init_sentry(
    dsn: Optional[str] = None,
    environment: str = "development",
    traces_sample_rate: float = 1.0,
    profiles_sample_rate: float = 1.0,
) -> None:
    """Initialize Sentry SDK with proper configuration.
    
    Args:
        dsn: Sentry DSN. If not provided, will try to get from SENTRY_DSN env var
        environment: Environment name (development, production, etc.)
        traces_sample_rate: Sample rate for performance monitoring
        profiles_sample_rate: Sample rate for profiling
    """
    # Check if Sentry is explicitly disabled
    if os.getenv('DISABLE_SENTRY', '').lower() in ('true', '1', 'yes'):
        logger.info("Sentry is disabled via DISABLE_SENTRY environment variable")
        return
    
    dsn = dsn or os.getenv('SENTRY_DSN')
    if not dsn:
        logger.warning("Sentry DSN not provided, skipping Sentry initialization")
        return

    # Configure logging integration
    logging_integration = LoggingIntegration(
        level=logging.INFO,        # Capture info and above as breadcrumbs
        event_level=logging.ERROR  # Send errors as events
    )

    # Initialize Sentry
    sentry_sdk.init(
        dsn=dsn,
        environment=environment,
        integrations=[
            logging_integration,
            ThreadingIntegration(propagate_hub=True),
        ],
        traces_sample_rate=traces_sample_rate,
        profiles_sample_rate=profiles_sample_rate,
        
        # Enable performance monitoring
        enable_tracing=True,
        
        # Configure what to include/exclude in error reports
        send_default_pii=False,
        max_breadcrumbs=50,
        attach_stacktrace=True,
        
        # Add release info if available
        release=os.getenv('RELEASE_VERSION', 'development'),
    )

    logger.info(f"Sentry initialized for environment: {environment}")

def capture_error(error: Exception, extra_data: Optional[Dict[str, Any]] = None) -> None:
    """Capture an error with additional context.
    
    Args:
        error: The exception to capture
        extra_data: Additional context data to attach to the error
    """
    if extra_data:
        with sentry_sdk.push_scope() as scope:
            for key, value in extra_data.items():
                scope.set_extra(key, value)
            sentry_sdk.capture_exception(error)
    else:
        sentry_sdk.capture_exception(error)

def add_breadcrumb(
    message: str,
    category: Optional[str] = None,
    level: str = "info",
    data: Optional[Dict[str, Any]] = None
) -> None:
    """Add a breadcrumb for debugging.
    
    Args:
        message: Breadcrumb message
        category: Category for grouping breadcrumbs
        level: Severity level (debug, info, warning, error)
        data: Additional structured data
    """
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data
    )

def monitor_errors(func):
    """Decorator to monitor function execution and capture errors in Sentry.
    
    Usage:
        @monitor_errors
        def my_function():
            ...
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Add context about the function
            extra_data = {
                'function': func.__name__,
                'args': repr(args),
                'kwargs': repr(kwargs)
            }
            capture_error(e, extra_data)
            raise  # Re-raise the exception after capturing
    return wrapper 