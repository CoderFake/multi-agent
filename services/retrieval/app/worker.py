"""RabbitMQ consumers for the retrieval microservice.

Two consumers run in background daemon threads:

1. **Indexing consumer** — listens on `indexing_tasks` queue for document
   indexing requests dispatched by the main backend.

2. **RAG RPC consumer** — listens on `rag_requests` queue for search/file
   queries from sagent.  Processes the request and publishes the response
   back to the caller's `reply_to` queue with matching `correlation_id`.

Message format (RAG RPC):
    Request:  {"action": "search"|"list_files", ...payload}
    Response: JSON-serialized SearchResponse / ListFilesResponse
"""

import asyncio
import json
import logging
import threading

import pika

from app.config import settings
from app.schemas.files import ListFilesRequest
from app.schemas.index import IndexRequest
from app.schemas.search import SearchRequest
from app.services.file_service import file_svc
from app.services.index_service import index_svc
from app.services.search_service import search_svc

logger = logging.getLogger(__name__)


# ── Indexing consumer ──────────────────────────────────────────────────

def _process_indexing(ch, method, _properties, body):
    """Process a single indexing task from RabbitMQ."""
    try:
        payload = json.loads(body)
        request = IndexRequest.model_validate(payload)
        logger.info(
            f"Processing indexing task: {len(request.documents)} docs → "
            f"{request.collection_name}"
        )
        asyncio.get_event_loop().run_until_complete(
            index_svc.index_documents(request)
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)
    except Exception as e:
        logger.exception(f"Failed to process indexing task: {e}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)


# ── RAG RPC consumer ──────────────────────────────────────────────────

def _process_rag_request(ch, method, properties, body):
    """Process a RAG RPC request and reply to the caller.

    Expected payload: {"action": "search"|"list_files", ...fields}
    Publishes JSON response to properties.reply_to with matching correlation_id.
    """
    try:
        payload = json.loads(body)
        action = payload.pop("action", None)
        logger.info(f"RAG RPC request: action={action}")

        if action == "search":
            request = SearchRequest.model_validate(payload)
            result = asyncio.get_event_loop().run_until_complete(
                search_svc.search(request)
            )
            response_body = result.model_dump_json()

        elif action == "list_files":
            request = ListFilesRequest.model_validate(payload)
            result = asyncio.get_event_loop().run_until_complete(
                file_svc.list_files(request)
            )
            response_body = result.model_dump_json()

        else:
            response_body = json.dumps({"error": f"Unknown action: {action}"})

    except Exception as e:
        logger.exception(f"RAG RPC processing failed: {e}")
        response_body = json.dumps({"error": str(e)})

    # Publish response back to caller
    if properties.reply_to:
        ch.basic_publish(
            exchange="",
            routing_key=properties.reply_to,
            properties=pika.BasicProperties(
                correlation_id=properties.correlation_id,
                content_type="application/json",
            ),
            body=response_body,
        )

    ch.basic_ack(delivery_tag=method.delivery_tag)


# ── Consumer runners ──────────────────────────────────────────────────

def _run_indexing_consumer():
    """Run the indexing queue consumer (blocking)."""
    try:
        params = pika.URLParameters(settings.RABBITMQ_URL)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()

        channel.queue_declare(queue=settings.QUEUE_INDEXING, durable=True)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=settings.QUEUE_INDEXING, on_message_callback=_process_indexing)

        logger.info(f"Indexing consumer listening on queue: {settings.QUEUE_INDEXING}")
        channel.start_consuming()
    except Exception as e:
        logger.error(f"Indexing consumer error: {e}")


def _run_rag_consumer():
    """Run the RAG RPC queue consumer (blocking)."""
    try:
        params = pika.URLParameters(settings.RABBITMQ_URL)
        connection = pika.BlockingConnection(params)
        channel = connection.channel()

        channel.queue_declare(queue=settings.QUEUE_RAG_REQUESTS, durable=True)
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=settings.QUEUE_RAG_REQUESTS, on_message_callback=_process_rag_request)

        logger.info(f"RAG RPC consumer listening on queue: {settings.QUEUE_RAG_REQUESTS}")
        channel.start_consuming()
    except Exception as e:
        logger.error(f"RAG RPC consumer error: {e}")


def start_consumers():
    """Start all RabbitMQ consumers in background daemon threads."""
    threads = []
    for name, target in [
        ("rabbitmq-indexing", _run_indexing_consumer),
        ("rabbitmq-rag-rpc", _run_rag_consumer),
    ]:
        t = threading.Thread(target=target, daemon=True, name=name)
        t.start()
        threads.append(t)
    return threads

