"""
NovaSaaS Customer Success - Kafka Client

Async Kafka producer and consumer using aiokafka.
"""
import asyncio
import json
import structlog
from datetime import datetime
from typing import Optional, Dict, Any, Callable, Awaitable, List
from enum import Enum

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.errors import KafkaError

logger = structlog.get_logger()


# =============================================================================
# Topic Definitions
# =============================================================================

class KafkaTopics(str, Enum):
    """Kafka topic names for NovaSaaS event streaming"""
    
    # Ticket events
    TICKETS_INCOMING = "fte.tickets.incoming"
    TICKETS_CREATED = "fte.tickets.created"
    TICKETS_UPDATED = "fte.tickets.updated"
    TICKETS_RESOLVED = "fte.tickets.resolved"
    
    # Channel inbound events
    CHANNELS_EMAIL_INBOUND = "fte.channels.email.inbound"
    CHANNELS_WHATSAPP_INBOUND = "fte.channels.whatsapp.inbound"
    CHANNELS_WEBFORM_INBOUND = "fte.channels.webform.inbound"
    
    # Escalation events
    ESCALATIONS = "fte.escalations"
    
    # Metrics events
    METRICS = "fte.metrics"
    
    # Dead Letter Queue
    DLQ = "fte.dlq"
    
    # Agent events
    AGENT_REQUESTS = "fte.agent.requests"
    AGENT_RESPONSES = "fte.agent.responses"


# Topic list for easy iteration
ALL_TOPICS = [topic.value for topic in KafkaTopics]

# Inbound topics (messages from customers)
INBOUND_TOPICS = [
    KafkaTopics.TICKETS_INCOMING.value,
    KafkaTopics.CHANNELS_EMAIL_INBOUND.value,
    KafkaTopics.CHANNELS_WHATSAPP_INBOUND.value,
    KafkaTopics.CHANNELS_WEBFORM_INBOUND.value,
]


# =============================================================================
# Kafka Producer
# =============================================================================

class FTEKafkaProducer:
    """
    FastTrack Enterprise Kafka Producer with aiokafka.
    
    Features:
    - Automatic timestamp injection
    - JSON serialization
    - Structured logging
    - Connection management
    """
    
    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        client_id: str = "novasaas-producer",
        enable_idempotence: bool = True,
        acks: str = "all",
        retries: int = 3,
    ):
        """
        Initialize Kafka producer.
        
        Args:
            bootstrap_servers: Kafka broker addresses
            client_id: Client identifier for this producer
            enable_idempotence: Enable exactly-once semantics
            acks: Acknowledgment level ("all", "1", "0")
            retries: Number of retries on failure
        """
        self.bootstrap_servers = bootstrap_servers
        self.client_id = client_id
        self._producer: Optional[AIOKafkaProducer] = None
        
        self._producer_config = {
            "bootstrap_servers": bootstrap_servers,
            "client_id": client_id,
            "enable_idempotence": enable_idempotence,
            "acks": acks,
            "retries": retries,
            "retry_backoff_ms": 100,
            "value_serializer": lambda v: json.dumps(v, default=str).encode("utf-8"),
            "key_serializer": lambda k: k.encode("utf-8") if k else None,
        }
        
        logger.info(
            "FTEKafkaProducer initialized",
            bootstrap_servers=bootstrap_servers,
            client_id=client_id
        )
    
    async def start(self) -> None:
        """Start the Kafka producer connection"""
        if self._producer is None:
            self._producer = AIOKafkaProducer(**self._producer_config)
            await self._producer.start()
            logger.info("Kafka producer started")
    
    async def stop(self) -> None:
        """Stop the Kafka producer connection"""
        if self._producer:
            await self._producer.stop()
            self._producer = None
            logger.info("Kafka producer stopped")
    
    async def publish(
        self,
        topic: str,
        event: Dict[str, Any],
        key: Optional[str] = None,
        headers: Optional[List[tuple]] = None,
    ) -> Dict[str, Any]:
        """
        Publish an event to a Kafka topic.
        
        Automatically adds timestamp and metadata to the event.
        
        Args:
            topic: Kafka topic name
            event: Event data (will be JSON serialized)
            key: Optional message key for partitioning
            headers: Optional Kafka headers
        
        Returns:
            Dict with publish result including topic, partition, offset
        
        Raises:
            KafkaError: If publishing fails
        """
        if not self._producer:
            await self.start()
        
        # Add metadata
        enriched_event = {
            **event,
            "_timestamp": datetime.utcnow().isoformat(),
            "_source": self.client_id,
        }
        
        start_time = datetime.utcnow()
        
        try:
            metadata = await self._producer.send_and_wait(
                topic,
                value=enriched_event,
                key=key,
                headers=headers,
            )
            
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            logger.debug(
                "Event published",
                topic=topic,
                key=key,
                partition=metadata.partition,
                offset=metadata.offset,
                latency_ms=round(latency_ms, 2)
            )
            
            return {
                "status": "success",
                "topic": topic,
                "partition": metadata.partition,
                "offset": metadata.offset,
                "timestamp": enriched_event["_timestamp"],
                "latency_ms": round(latency_ms, 2),
            }
            
        except KafkaError as error:
            logger.error(
                "Failed to publish event",
                topic=topic,
                key=key,
                error=str(error)
            )
            raise
    
    async def publish_batch(
        self,
        topic: str,
        events: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Publish multiple events to a topic in a batch.
        
        Args:
            topic: Kafka topic name
            events: List of event dicts
        
        Returns:
            List of publish results
        """
        if not self._producer:
            await self.start()
        
        results = []
        
        for event in events:
            key = event.get("id") or event.get("ticket_id")
            try:
                result = await self.publish(topic, event, key=str(key))
                results.append(result)
            except KafkaError as error:
                results.append({
                    "status": "error",
                    "topic": topic,
                    "key": key,
                    "error": str(error),
                })
        
        return results
    
    async def send_to_dlq(
        self,
        original_topic: str,
        message: Dict[str, Any],
        error: str,
        error_type: str = "processing_error",
    ) -> Dict[str, Any]:
        """
        Send a failed message to the Dead Letter Queue.
        
        Args:
            original_topic: The topic where the message originally came from
            message: The original message that failed
            error: Error message
            error_type: Type of error
        
        Returns:
            Publish result
        """
        dlq_event = {
            "original_topic": original_topic,
            "original_message": message,
            "error": error,
            "error_type": error_type,
            "failed_at": datetime.utcnow().isoformat(),
        }
        
        return await self.publish(
            KafkaTopics.DLQ.value,
            dlq_event,
            key=message.get("id") or message.get("ticket_id"),
        )


# =============================================================================
# Kafka Consumer
# =============================================================================

class FTEKafkaConsumer:
    """
    FastTrack Enterprise Kafka Consumer with aiokafka.
    
    Features:
    - Callback-based message handling
    - Automatic deserialization
    - Error handling with DLQ support
    - Structured logging
    """
    
    def __init__(
        self,
        bootstrap_servers: str = "localhost:9092",
        group_id: str = "novasaas-consumer",
        client_id: str = "novasaas-consumer",
        auto_offset_reset: str = "latest",
        enable_auto_commit: bool = False,
        max_poll_records: int = 100,
        session_timeout_ms: int = 30000,
        heartbeat_interval_ms: int = 10000,
    ):
        """
        Initialize Kafka consumer.
        
        Args:
            bootstrap_servers: Kafka broker addresses
            group_id: Consumer group ID
            client_id: Client identifier
            auto_offset_reset: Where to start reading (earliest/latest)
            enable_auto_commit: Auto-commit offsets
            max_poll_records: Max records per poll
            session_timeout_ms: Session timeout
            heartbeat_interval_ms: Heartbeat interval
        """
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.client_id = client_id
        self._consumer: Optional[AIOKafkaConsumer] = None
        
        self._consumer_config = {
            "bootstrap_servers": bootstrap_servers,
            "group_id": group_id,
            "client_id": client_id,
            "auto_offset_reset": auto_offset_reset,
            "enable_auto_commit": enable_auto_commit,
            "max_poll_records": max_poll_records,
            "session_timeout_ms": session_timeout_ms,
            "heartbeat_interval_ms": heartbeat_interval_ms,
            "value_deserializer": lambda v: json.loads(v.decode("utf-8")) if v else None,
            "key_deserializer": lambda k: k.decode("utf-8") if k else None,
        }
        
        self._running = False
        self._handler: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None
        
        logger.info(
            "FTEKafkaConsumer initialized",
            bootstrap_servers=bootstrap_servers,
            group_id=group_id
        )
    
    async def start(self, topics: List[str]) -> None:
        """
        Start the Kafka consumer and subscribe to topics.
        
        Args:
            topics: List of topic names to subscribe to
        """
        if self._consumer is None:
            self._consumer = AIOKafkaConsumer(**self._consumer_config)
            await self._consumer.start()
            self._consumer.subscribe(topics)
            logger.info("Kafka consumer started", topics=topics)
    
    async def stop(self) -> None:
        """Stop the Kafka consumer"""
        self._running = False
        if self._consumer:
            await self._consumer.stop()
            self._consumer = None
            logger.info("Kafka consumer stopped")
    
    def set_handler(
        self,
        handler: Callable[[str, Dict[str, Any]], Awaitable[None]]
    ) -> None:
        """
        Set the message handler callback.
        
        Args:
            handler: Async function that takes (topic, message) and returns None
        """
        self._handler = handler
        logger.info("Message handler set")
    
    async def consume(
        self,
        handler: Optional[Callable[[str, Dict[str, Any]], Awaitable[None]]] = None,
        error_handler: Optional[Callable[[str, Dict[str, Any], Exception], Awaitable[None]]] = None,
    ) -> None:
        """
        Start consuming messages with the given handler.
        
        Args:
            handler: Message handler callback (topic, message) -> None
            error_handler: Optional error handler (topic, message, error) -> None
        """
        if handler:
            self.set_handler(handler)
        
        if not self._handler:
            raise ValueError("No message handler set. Call set_handler() first.")
        
        if not self._consumer:
            await self.start(list(self._consumer.subscription()))
        
        self._running = True
        logger.info("Starting message consumption")
        
        while self._running:
            try:
                async for msg in self._consumer:
                    if not self._running:
                        break
                    
                    topic = msg.topic
                    key = msg.key
                    value = msg.value
                    offset = msg.offset
                    partition = msg.partition
                    
                    start_time = datetime.utcnow()
                    
                    try:
                        # Call the handler
                        await self._handler(topic, value)
                        
                        # Commit offset after successful processing
                        await self._consumer.commit()
                        
                        latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
                        
                        logger.debug(
                            "Message processed",
                            topic=topic,
                            key=key,
                            offset=offset,
                            latency_ms=round(latency_ms, 2)
                        )
                        
                    except Exception as error:
                        logger.error(
                            "Error processing message",
                            topic=topic,
                            key=key,
                            offset=offset,
                            error=str(error)
                        )
                        
                        if error_handler:
                            await error_handler(topic, value, error)
                        
                        # Don't commit offset on error - will retry
                        # Or commit to skip bad messages (uncomment below)
                        # await self._consumer.commit()
                        
            except KafkaError as error:
                logger.error("Kafka consumer error", error=str(error))
                await asyncio.sleep(5)  # Back off before reconnecting
            except asyncio.CancelledError:
                logger.info("Consumer cancelled")
                break
        
        logger.info("Message consumption stopped")
    
    async def get_message(self, timeout_ms: int = 1000) -> Optional[Dict[str, Any]]:
        """
        Get a single message (for testing).
        
        Args:
            timeout_ms: Timeout in milliseconds
        
        Returns:
            Message value or None if timeout
        """
        if not self._consumer:
            return None
        
        try:
            msg = await asyncio.wait_for(
                self._consumer.getone(),
                timeout=timeout_ms / 1000
            )
            return msg.value if msg else None
        except asyncio.TimeoutError:
            return None


# =============================================================================
# Factory Functions
# =============================================================================

def create_producer(
    bootstrap_servers: str = "localhost:9092",
    client_id: str = "novasaas-producer",
) -> FTEKafkaProducer:
    """Create a Kafka producer instance"""
    return FTEKafkaProducer(
        bootstrap_servers=bootstrap_servers,
        client_id=client_id,
    )


def create_consumer(
    bootstrap_servers: str = "localhost:9092",
    group_id: str = "novasaas-consumer",
    client_id: str = "novasaas-consumer",
) -> FTEKafkaConsumer:
    """Create a Kafka consumer instance"""
    return FTEKafkaConsumer(
        bootstrap_servers=bootstrap_servers,
        group_id=group_id,
        client_id=client_id,
    )


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Classes
    "FTEKafkaProducer",
    "FTEKafkaConsumer",
    # Topics
    "KafkaTopics",
    "ALL_TOPICS",
    "INBOUND_TOPICS",
    # Factories
    "create_producer",
    "create_consumer",
]
