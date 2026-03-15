"""Worker — RabbitMQ consumers + Redis indexing consumer.

Runs in background threads alongside the FastAPI application.
"""

from __future__ import annotations

import asyncio
import json
import logging
import threading
import traceback
from typing import Optional

import pika

from app.config.settings import settings
from app.core.redis import pop_task
from app.schemas.events import IndexTaskPayload

logger = logging.getLogger(__name__)


# ── Redis Indexing Consumer ───────────────────────────────────────────

def _run_indexing_consumer_sync():
    """
    Blocking consumer: BRPOP idx:queue, process each indexing task.
    Runs in a dedicated thread.
    """
    logger.info("Redis indexing consumer started")

    # Create a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while True:
        try:
            task_data = pop_task(timeout=5)
            if task_data is None:
                continue

            payload = IndexTaskPayload(**task_data)
            logger.info(
                "Indexing task received: job=%s doc=%s",
                payload.job_id, payload.document_id,
            )

            # Import here to avoid circular imports
            from app.services.index_service import process_indexing_task

            loop.run_until_complete(process_indexing_task(payload))

        except Exception as e:
            logger.error("Indexing consumer error: %s", e)
            logger.error(traceback.format_exc())


def start_indexing_consumer():
    """Start the Redis indexing consumer in a daemon thread."""
    thread = threading.Thread(
        target=_run_indexing_consumer_sync,
        name="indexing-consumer",
        daemon=True,
    )
    thread.start()
    logger.info("Indexing consumer thread started")
    return thread


# ── RabbitMQ RAG Consumer ─────────────────────────────────────────────

def _on_rag_request(ch, method, properties, body):
    """Handle RAG RPC request from RabbitMQ."""
    try:
        data = json.loads(body)
        query = data.get("query", "")
        org_id = data.get("org_id", "")
        org_subdomain = data.get("org_subdomain", "")
        agent_code = data.get("agent_code", "")
        user_group_ids = data.get("user_group_ids", [])
        user_role = data.get("user_role", "member")
        top_k = data.get("top_k", settings.DEFAULT_TOP_K)

        # Import here to avoid circular imports
        from app.services.search_service import search
        loop = asyncio.new_event_loop()
        results = loop.run_until_complete(
            search(
                query=query,
                org_id=org_id,
                org_subdomain=org_subdomain,
                agent_code=agent_code,
                user_group_ids=user_group_ids,
                user_role=user_role,
                top_k=top_k,
            )
        )
        loop.close()

        response = json.dumps({"results": results})
    except Exception as e:
        logger.error("RAG request error: %s", e)
        response = json.dumps({"results": [], "error": str(e)})

    # RPC reply
    if properties.reply_to:
        ch.basic_publish(
            exchange="",
            routing_key=properties.reply_to,
            properties=pika.BasicProperties(
                correlation_id=properties.correlation_id,
            ),
            body=response.encode(),
        )
    ch.basic_ack(delivery_tag=method.delivery_tag)


def _run_rabbitmq_consumer():
    """RabbitMQ consumer for RAG RPC requests."""
    try:
        params = pika.URLParameters(settings.RABBITMQ_URL)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()

        channel.queue_declare(queue=settings.QUEUE_RAG_REQUESTS, durable=True)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(
            queue=settings.QUEUE_RAG_REQUESTS,
            on_message_callback=_on_rag_request,
        )

        logger.info("RabbitMQ RAG consumer started on %s", settings.QUEUE_RAG_REQUESTS)
        channel.start_consuming()
    except Exception as e:
        logger.error("RabbitMQ consumer failed: %s", e)
        logger.error(traceback.format_exc())


def start_rabbitmq_consumer():
    """Start the RabbitMQ consumer in a daemon thread."""
    thread = threading.Thread(
        target=_run_rabbitmq_consumer,
        name="rabbitmq-consumer",
        daemon=True,
    )
    thread.start()
    logger.info("RabbitMQ consumer thread started")
    return thread
