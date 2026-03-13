"""
RabbitMQ publisher singleton — publishes messages to queues.
Uses pika (sync) wrapped in asyncio.to_thread for non-blocking.
"""
import json
import uuid
from typing import Any, Dict, Optional

import pika

from app.config.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

_connection: Optional[pika.BlockingConnection] = None
_channel: Optional[pika.channel.Channel] = None

EMAIL_QUEUE = "email_tasks"


def _get_channel() -> pika.channel.Channel:
    """Get or create RabbitMQ channel singleton."""
    global _connection, _channel

    if _connection is None or _connection.is_closed:
        params = pika.URLParameters(settings.RABBITMQ_URL)
        _connection = pika.BlockingConnection(params)
        _channel = _connection.channel()
        _channel.queue_declare(queue=EMAIL_QUEUE, durable=True)
        logger.info("RabbitMQ connection established")

    if _channel is None or _channel.is_closed:
        _channel = _connection.channel()
        _channel.queue_declare(queue=EMAIL_QUEUE, durable=True)

    return _channel


def publish_email_task(
    template_name: str,
    recipient_email: str,
    subject: str,
    context: Dict[str, Any],
    priority: int = 5,
) -> str:
    """
    Publish email task to RabbitMQ (sync — call via asyncio.to_thread).

    Returns:
        task_id
    """
    task_id = str(uuid.uuid4())
    message = {
        "task_id": task_id,
        "template_name": template_name,
        "recipient_email": recipient_email,
        "subject": subject,
        "context": context,
        "priority": priority,
    }

    channel = _get_channel()
    channel.basic_publish(
        exchange="",
        routing_key=EMAIL_QUEUE,
        body=json.dumps(message),
        properties=pika.BasicProperties(
            delivery_mode=2,  # persistent
            content_type="application/json",
        ),
    )
    logger.info(f"Email task published: {task_id} → {recipient_email}")
    return task_id
