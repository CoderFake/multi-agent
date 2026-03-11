"""RabbitMQ RPC client for communicating with the retrieval microservice.

Implements the RPC pattern:
1. sagent publishes a request to `rag_requests` queue with a correlation_id and reply_to
2. retrieval consumes, processes, publishes response to the reply_to queue
3. sagent waits for the correlated response

Usage:
    from core.queue import rag_rpc

    result = rag_rpc.call("search", {"query": "...", "collection_names": [...]})
"""

import json
import logging
import threading
import uuid

import pika

from config.settings import settings

logger = logging.getLogger(__name__)


class RagRpcClient:
    """Blocking RPC client for RAG requests via RabbitMQ."""

    def __init__(self) -> None:
        self._connection: pika.BlockingConnection | None = None
        self._channel: pika.adapters.blocking_connection.BlockingChannel | None = None
        self._callback_queue: str = ""
        self._responses: dict[str, dict | None] = {}
        self._lock = threading.Lock()

    def _ensure_connection(self) -> None:
        """Lazily create connection and declare exclusive callback queue."""
        if self._connection and self._connection.is_open:
            return

        params = pika.URLParameters(settings.RABBITMQ_URL)
        self._connection = pika.BlockingConnection(params)
        self._channel = self._connection.channel()

        # Declare the request queue (durable, shared with retrieval)
        self._channel.queue_declare(queue=settings.QUEUE_RAG_REQUESTS, durable=True)

        # Exclusive callback queue for responses (auto-delete)
        result = self._channel.queue_declare(queue="", exclusive=True)
        self._callback_queue = result.method.queue

        self._channel.basic_consume(
            queue=self._callback_queue,
            on_message_callback=self._on_response,
            auto_ack=True,
        )

    def _on_response(self, _ch, _method, properties, body) -> None:
        """Handle response messages on the callback queue."""
        corr_id = properties.correlation_id
        if corr_id in self._responses:
            try:
                self._responses[corr_id] = json.loads(body)
            except json.JSONDecodeError:
                logger.error(f"Invalid JSON response for correlation_id={corr_id}")
                self._responses[corr_id] = {"error": "Invalid JSON response"}

    def call(self, action: str, payload: dict, timeout: int | None = None) -> dict:
        """Publish an RPC request and wait for the response.

        Args:
            action: The action type ("search" or "list_files").
            payload: The request payload (will be JSON-serialized).
            timeout: Max seconds to wait. Defaults to settings.RAG_RPC_TIMEOUT.

        Returns:
            Parsed JSON response dict from retrieval service.

        Raises:
            TimeoutError: If no response received within timeout.
            ConnectionError: If RabbitMQ is unreachable.
        """
        if timeout is None:
            timeout = settings.RAG_RPC_TIMEOUT

        corr_id = str(uuid.uuid4())
        message = {"action": action, **payload}

        with self._lock:
            try:
                self._ensure_connection()
            except Exception as e:
                logger.error(f"RabbitMQ connection failed: {e}")
                raise ConnectionError(f"Cannot connect to RabbitMQ: {e}") from e

            self._responses[corr_id] = None

            self._channel.basic_publish(
                exchange="",
                routing_key=settings.QUEUE_RAG_REQUESTS,
                properties=pika.BasicProperties(
                    reply_to=self._callback_queue,
                    correlation_id=corr_id,
                    content_type="application/json",
                    delivery_mode=2,  # persistent
                ),
                body=json.dumps(message),
            )

            # Poll for response
            elapsed = 0.0
            while self._responses[corr_id] is None and elapsed < timeout:
                self._connection.process_data_events(time_limit=0.5)
                elapsed += 0.5

            response = self._responses.pop(corr_id, None)

        if response is None:
            raise TimeoutError(f"RAG RPC timeout after {timeout}s (action={action})")

        return response

    def close(self) -> None:
        """Close the RabbitMQ connection."""
        if self._connection and self._connection.is_open:
            try:
                self._connection.close()
            except Exception:
                pass
        self._connection = None
        self._channel = None


# Module-level singleton
rag_rpc = RagRpcClient()

