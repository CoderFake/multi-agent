"""
Email queue utility — publishes email tasks to RabbitMQ (non-blocking).
"""
import asyncio
from typing import Dict, Any

from app.services.rabbitmq import publish_email_task
from app.utils.logging import get_logger

logger = get_logger(__name__)


async def queue_email(
    template_name: str,
    recipient_email: str,
    subject: str,
    context: Dict[str, Any],
    priority: int = 5,
) -> str:
    """
    Queue email task to RabbitMQ (non-blocking).

    Args:
        template_name: Email template filename (in app/static/templates/)
        recipient_email: Recipient email address
        subject: Email subject
        context: Template context data
        priority: Task priority (0-10, higher = more priority)

    Returns:
        task_id
    """
    try:
        task_id = await asyncio.to_thread(
            publish_email_task,
            template_name=template_name,
            recipient_email=recipient_email,
            subject=subject,
            context=context,
            priority=priority,
        )
        logger.info(f"Email queued: {task_id} → {recipient_email} ({template_name})")
        return task_id
    except Exception as e:
        logger.error(f"Failed to queue email to {recipient_email}: {e}", exc_info=True)
        raise
