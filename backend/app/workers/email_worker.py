"""
Email worker — consumes email tasks from RabbitMQ and sends via SMTP.
Run as a separate process: python -m app.workers.email_worker
"""
import json
import smtplib
import os
import sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

import pika

# Add backend dir to path for imports
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.config.settings import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "static" / "templates"
EMAIL_QUEUE = "email_tasks"


def _render_template(template_name: str, context: dict) -> str:
    """Render HTML template with context vars."""
    template_path = TEMPLATE_DIR / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")

    html = template_path.read_text(encoding="utf-8")
    for key, value in context.items():
        html = html.replace(f"{{{{{key}}}}}", str(value))
    return html


def _send_email(recipient: str, subject: str, html_body: str) -> None:
    """Send email via SMTP."""
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_FROM
    msg["To"] = recipient
    msg.attach(MIMEText(html_body, "html"))

    try:
        if settings.SMTP_USE_TLS:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
            server.starttls()
        else:
            server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)

        if settings.SMTP_USER:
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)

        server.sendmail(settings.SMTP_FROM, recipient, msg.as_string())
        server.quit()
        logger.info(f"Email sent to {recipient}: {subject}")
    except Exception as e:
        logger.error(f"SMTP send failed to {recipient}: {e}", exc_info=True)
        raise


def _on_message(ch, method, properties, body):
    """Process email task from queue."""
    try:
        task = json.loads(body)
        task_id = task.get("task_id", "unknown")
        template_name = task["template_name"]
        recipient = task["recipient_email"]
        subject = task["subject"]
        context = task["context"]

        logger.info(f"Processing email task {task_id} → {recipient}")

        html = _render_template(template_name, context)
        _send_email(recipient, subject, html)

        ch.basic_ack(delivery_tag=method.delivery_tag)
        logger.info(f"Email task {task_id} completed")
    except Exception as e:
        logger.error(f"Email task failed: {e}", exc_info=True)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def main():
    """Start email worker — consume from RabbitMQ."""
    logger.info("Email worker starting...")
    params = pika.URLParameters(settings.RABBITMQ_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue=EMAIL_QUEUE, durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=EMAIL_QUEUE, on_message_callback=_on_message)

    logger.info(f"Email worker listening on queue: {EMAIL_QUEUE}")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
    finally:
        connection.close()
        logger.info("Email worker stopped")


if __name__ == "__main__":
    main()
