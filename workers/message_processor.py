"""
NovaSaaS Customer Success - Unified Message Processor

Kafka worker that processes incoming messages from all channels,
resolves customers, manages conversations, and runs the AI agent.
"""
import asyncio
import asyncpg
import structlog
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

from kafka_client import (
    FTEKafkaProducer,
    FTEKafkaConsumer,
    KafkaTopics,
    INBOUND_TOPICS,
    create_producer,
    create_consumer,
)

logger = structlog.get_logger()

# Database pool (injected)
_db_pool: Optional[asyncpg.Pool] = None

# Kafka clients
_producer: Optional[FTEKafkaProducer] = None
_consumer: Optional[FTEKafkaConsumer] = None


def set_db_pool(pool: asyncpg.Pool) -> None:
    """Set the database connection pool"""
    global _db_pool
    _db_pool = pool
    logger.info("Database pool set for message processor")


def set_kafka_clients(
    producer: FTEKafkaProducer,
    consumer: FTEKafkaConsumer,
) -> None:
    """Set Kafka producer and consumer"""
    global _producer, _consumer
    _producer = producer
    _consumer = consumer
    logger.info("Kafka clients set for message processor")


# =============================================================================
# Unified Message Processor
# =============================================================================

class UnifiedMessageProcessor:
    """
    Unified processor for all inbound messages.
    
    Pipeline:
    1. Resolve or create customer (by email or phone)
    2. Get or create conversation (reuses active within 24h)
    3. Store inbound message
    4. Run AI agent for response
    5. Store outbound response
    6. Publish metrics
    7. Handle errors with DLQ
    """
    
    def __init__(
        self,
        db_pool: Optional[asyncpg.Pool] = None,
        producer: Optional[FTEKafkaProducer] = None,
    ):
        """
        Initialize the message processor.
        
        Args:
            db_pool: AsyncPG connection pool
            producer: Kafka producer for outbound events
        """
        self._db_pool = db_pool or _db_pool
        self._producer = producer or _producer
        
        # Processing statistics
        self._stats = {
            "processed": 0,
            "errors": 0,
            "total_latency_ms": 0,
        }
        
        logger.info("UnifiedMessageProcessor initialized")
    
    @property
    def db_pool(self) -> asyncpg.Pool:
        """Get database pool"""
        if not self._db_pool:
            raise RuntimeError("Database pool not set. Call set_db_pool() first.")
        return self._db_pool
    
    @property
    def producer(self) -> FTEKafkaProducer:
        """Get Kafka producer"""
        if not self._producer:
            raise RuntimeError("Kafka producer not set. Call set_kafka_clients() first.")
        return self._producer
    
    async def resolve_customer(
        self,
        message: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Find or create a customer in PostgreSQL by email or phone.
        
        Args:
            message: Normalized message dict with customer_email or customer_phone
        
        Returns:
            Customer dict with id, name, email, etc.
        """
        customer_email = message.get("customer_email")
        customer_phone = message.get("customer_phone")
        customer_name = message.get("customer_name")
        channel = message.get("channel", "unknown")
        
        async with self.db_pool.acquire() as conn:
            # Try to find by email first
            if customer_email:
                customer = await conn.fetchrow(
                    """
                    SELECT id, name, email, company, tier, created_at
                    FROM customers
                    WHERE email = $1
                    """,
                    customer_email
                )
                
                if customer:
                    logger.info(
                        "Customer found by email",
                        customer_id=customer["id"],
                        email=customer_email
                    )
                    return dict(customer)
            
            # Try to find by phone
            if customer_phone:
                # Look up in channel identifiers
                result = await conn.fetchrow(
                    """
                    SELECT c.id, c.name, c.email, c.company, c.tier, c.created_at
                    FROM customers c
                    JOIN customer_channel_identifiers cci ON c.id = cci.customer_id
                    WHERE cci.channel_type = 'phone' AND cci.channel_id = $1
                    """,
                    customer_phone
                )
                
                if result:
                    logger.info(
                        "Customer found by phone",
                        customer_id=result["id"],
                        phone=customer_phone
                    )
                    return dict(result)
            
            # Create new customer
            logger.info(
                "Creating new customer",
                email=customer_email,
                phone=customer_phone,
                name=customer_name
            )
            
            # Generate a name if not provided
            if not customer_name:
                customer_name = customer_email.split("@")[0] if customer_email else f"Customer_{customer_phone}"
            
            customer_id = await conn.fetchval(
                """
                INSERT INTO customers (name, email, company, tier, created_at, updated_at)
                VALUES ($1, $2, $3, 'standard', NOW(), NOW())
                RETURNING id
                """,
                customer_name,
                customer_email,
                None  # Company
            )
            
            # Store channel identifier
            if customer_phone:
                await conn.execute(
                    """
                    INSERT INTO customer_channel_identifiers (customer_id, channel_type, channel_id, created_at)
                    VALUES ($1, 'phone', $2, NOW())
                    ON CONFLICT (customer_id, channel_type) DO NOTHING
                    """,
                    customer_id,
                    customer_phone
                )
            
            if customer_email:
                await conn.execute(
                    """
                    INSERT INTO customer_channel_identifiers (customer_id, channel_type, channel_id, created_at)
                    VALUES ($1, 'email', $2, NOW())
                    ON CONFLICT (customer_id, channel_type) DO NOTHING
                    """,
                    customer_id,
                    customer_email
                )
            
            logger.info("New customer created", customer_id=customer_id)
            
            return {
                "id": customer_id,
                "name": customer_name,
                "email": customer_email,
                "company": None,
                "tier": "standard",
                "created_at": datetime.utcnow(),
            }
    
    async def get_or_create_conversation(
        self,
        customer_id: int,
        channel: str,
    ) -> Dict[str, Any]:
        """
        Get active conversation or create new one.
        
        Reuses an active conversation within 24 hours.
        
        Args:
            customer_id: Customer ID
            channel: Channel name (email, whatsapp, web_form, etc.)
        
        Returns:
            Conversation dict with id, status, etc.
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        
        async with self.db_pool.acquire() as conn:
            # Look for active conversation within 24h
            conversation = await conn.fetchrow(
                """
                SELECT id, customer_id, channel, status, last_message_at, message_count
                FROM conversations
                WHERE customer_id = $1
                  AND channel = $2
                  AND status = 'active'
                  AND last_message_at > $3
                ORDER BY last_message_at DESC
                LIMIT 1
                """,
                customer_id,
                channel,
                cutoff_time
            )
            
            if conversation:
                logger.info(
                    "Found active conversation",
                    conversation_id=conversation["id"],
                    customer_id=customer_id,
                    channel=channel
                )
                return dict(conversation)
            
            # Create new conversation
            logger.info(
                "Creating new conversation",
                customer_id=customer_id,
                channel=channel
            )
            
            conversation_id = await conn.fetchval(
                """
                INSERT INTO conversations (customer_id, channel, status, last_message_at, message_count)
                VALUES ($1, $2, 'active', NOW(), 0)
                RETURNING id
                """,
                customer_id,
                channel
            )
            
            return {
                "id": conversation_id,
                "customer_id": customer_id,
                "channel": channel,
                "status": "active",
                "last_message_at": datetime.utcnow(),
                "message_count": 0,
            }
    
    async def store_message(
        self,
        conversation_id: int,
        message: Dict[str, Any],
        sender_type: str = "customer",
    ) -> Dict[str, Any]:
        """
        Store a message in the database.
        
        Args:
            conversation_id: Conversation ID
            message: Normalized message dict
            sender_type: 'customer', 'agent', 'system', or 'bot'
        
        Returns:
            Stored message dict with id
        """
        async with self.db_pool.acquire() as conn:
            # Get or create ticket for this conversation
            conversation = await conn.fetchrow(
                "SELECT customer_id, channel FROM conversations WHERE id = $1",
                conversation_id
            )
            
            if not conversation:
                raise ValueError(f"Conversation {conversation_id} not found")
            
            # Check if there's an existing ticket for this conversation
            ticket = await conn.fetchrow(
                """
                SELECT id FROM tickets
                WHERE customer_id = $1 AND channel = $2
                ORDER BY created_at DESC
                LIMIT 1
                """,
                conversation["customer_id"],
                conversation["channel"]
            )
            
            if not ticket:
                # Create new ticket
                ticket_id = await conn.fetchval(
                    """
                    INSERT INTO tickets (customer_id, subject, description, status, priority, channel, created_at, updated_at)
                    VALUES ($1, $2, $3, 'open', 'medium', $4, NOW(), NOW())
                    RETURNING id
                    """,
                    conversation["customer_id"],
                    message.get("subject") or f"Support request via {conversation['channel']}",
                    message.get("content", "")[:500],
                    conversation["channel"]
                )
            else:
                ticket_id = ticket["id"]
            
            # Store the message
            message_id = await conn.fetchval(
                """
                INSERT INTO ticket_messages (ticket_id, sender, sender_type, message, timestamp)
                VALUES ($1, $2, $3, $4, NOW())
                RETURNING id
                """,
                ticket_id,
                message.get("customer_name") or "Customer",
                sender_type,
                message.get("content", ""),
            )
            
            # Update conversation message count
            await conn.execute(
                """
                UPDATE conversations
                SET message_count = message_count + 1,
                    last_message_at = NOW()
                WHERE id = $1
                """,
                conversation_id
            )
            
            logger.info(
                "Message stored",
                message_id=message_id,
                ticket_id=ticket_id,
                conversation_id=conversation_id,
                sender_type=sender_type
            )
            
            return {
                "id": message_id,
                "ticket_id": ticket_id,
                "conversation_id": conversation_id,
                "sender_type": sender_type,
                "content": message.get("content", ""),
                "timestamp": datetime.utcnow().isoformat(),
            }
    
    async def run_agent(
        self,
        ticket_id: int,
        message: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Run the AI agent to generate a response.
        
        In production, this would call the customer_success_agent.
        For now, returns a simulated response.
        
        Args:
            ticket_id: Ticket ID
            message: Original customer message
        
        Returns:
            Agent response dict with message and metadata
        """
        logger.info("Running AI agent", ticket_id=ticket_id)
        
        # Simulate agent processing time
        await asyncio.sleep(0.1)
        
        # In production, this would call:
        # from agent.customer_success_agent import run_agent
        # response = await run_agent(
        #     message=message.get("content", ""),
        #     channel=message.get("channel", "web_form"),
        #     customer_id=customer_id
        # )
        
        # Simulated response
        response = {
            "message": f"Thank you for contacting NovaSaaS Support. We've received your message regarding '{message.get('subject', 'your request')}' and will respond shortly. Ticket #{ticket_id} has been created for tracking.",
            "action": "respond",
            "priority": "medium",
            "sentiment": 0.8,
            "confidence": 0.95,
        }
        
        logger.info(
            "Agent response generated",
            ticket_id=ticket_id,
            action=response["action"],
            sentiment=response["sentiment"]
        )
        
        return response
    
    async def store_outbound(
        self,
        ticket_id: int,
        response: Dict[str, Any],
        channel: str,
    ) -> Dict[str, Any]:
        """
        Store the agent's outbound response.
        
        Args:
            ticket_id: Ticket ID
            response: Agent response dict
            channel: Channel to send via
        
        Returns:
            Stored message dict
        """
        async with self.db_pool.acquire() as conn:
            message_id = await conn.fetchval(
                """
                INSERT INTO ticket_messages (ticket_id, sender, sender_type, message, timestamp)
                VALUES ($1, $2, $3, $4, NOW())
                RETURNING id
                """,
                ticket_id,
                "AI Agent",
                "agent",
                response.get("message", ""),
            )
            
            logger.info(
                "Outbound response stored",
                message_id=message_id,
                ticket_id=ticket_id
            )
            
            return {
                "id": message_id,
                "ticket_id": ticket_id,
                "sender_type": "agent",
                "content": response.get("message", ""),
                "timestamp": datetime.utcnow().isoformat(),
            }
    
    async def publish_metrics(
        self,
        topic: str,
        message: Dict[str, Any],
        latency_ms: float,
        success: bool = True,
    ) -> None:
        """
        Publish processing metrics to Kafka.
        
        Args:
            topic: Original topic the message came from
            message: Original message
            latency_ms: Processing latency in milliseconds
            success: Whether processing succeeded
        """
        metrics_event = {
            "event_type": "message_processed" if success else "message_failed",
            "source_topic": topic,
            "channel": message.get("channel", "unknown"),
            "customer_id": message.get("customer_id"),
            "ticket_id": message.get("ticket_id"),
            "conversation_id": message.get("conversation_id"),
            "latency_ms": round(latency_ms, 2),
            "timestamp": datetime.utcnow().isoformat(),
            "success": success,
        }
        
        try:
            await self.producer.publish(
                KafkaTopics.METRICS.value,
                metrics_event,
                key=str(message.get("ticket_id") or message.get("conversation_id")),
            )
        except Exception as error:
            logger.error("Failed to publish metrics", error=str(error))
    
    async def handle_error(
        self,
        topic: str,
        message: Dict[str, Any],
        error: Exception,
    ) -> None:
        """
        Handle processing errors.
        
        Sends apology via the correct channel and publishes to DLQ.
        
        Args:
            topic: Original topic
            message: Failed message
            error: Exception that occurred
        """
        logger.error(
            "Processing error",
            topic=topic,
            channel=message.get("channel"),
            error=str(error)
        )
        
        # Update stats
        self._stats["errors"] += 1
        
        # Send apology via the original channel
        channel = message.get("channel", "web_form")
        customer_email = message.get("customer_email")
        customer_phone = message.get("customer_phone")
        
        apology = {
            "message": "We apologize, but we encountered an error processing your message. A human agent has been notified and will contact you shortly. Reference: " + str(message.get("channel_message_id", "unknown")),
            "channel": channel,
        }
        
        # Try to send apology
        try:
            if channel == "email" and customer_email:
                # Would use GmailHandler here
                logger.info("Would send email apology", to=customer_email)
            elif channel == "whatsapp" and customer_phone:
                # Would use WhatsAppHandler here
                logger.info("Would send WhatsApp apology", to=customer_phone)
        except Exception as apology_error:
            logger.error("Failed to send apology", error=str(apology_error))
        
        # Publish to DLQ
        try:
            await self.producer.send_to_dlq(
                original_topic=topic,
                message=message,
                error=str(error),
                error_type=type(error).__name__,
            )
            logger.info("Message sent to DLQ", topic=topic)
        except Exception as dlq_error:
            logger.error("Failed to send to DLQ", error=str(dlq_error))
    
    async def process_message(
        self,
        topic: str,
        message: Dict[str, Any],
    ) -> None:
        """
        Full processing pipeline for an inbound message.
        
        Pipeline:
        1. Resolve customer → get conversation → store inbound
        2. Run agent → store outbound
        3. Publish metrics
        
        Args:
            topic: Kafka topic the message came from
            message: Normalized message dict
        """
        start_time = datetime.utcnow()
        
        logger.info(
            "Processing inbound message",
            topic=topic,
            channel=message.get("channel"),
            customer_email=message.get("customer_email"),
            customer_phone=message.get("customer_phone")
        )
        
        try:
            # Step 1: Resolve or create customer
            customer = await self.resolve_customer(message)
            customer_id = customer["id"]
            
            # Step 2: Get or create conversation
            channel = message.get("channel", "unknown")
            conversation = await self.get_or_create_conversation(customer_id, channel)
            conversation_id = conversation["id"]
            
            # Step 3: Store inbound message
            stored_inbound = await self.store_message(
                conversation_id,
                message,
                sender_type="customer"
            )
            ticket_id = stored_inbound["ticket_id"]
            
            # Update message with resolved IDs
            message["customer_id"] = customer_id
            message["conversation_id"] = conversation_id
            message["ticket_id"] = ticket_id
            
            # Step 4: Run AI agent
            agent_response = await self.run_agent(ticket_id, message)
            
            # Step 5: Store outbound response
            stored_outbound = await self.store_outbound(
                ticket_id,
                agent_response,
                channel
            )
            
            # Calculate latency
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Update stats
            self._stats["processed"] += 1
            self._stats["total_latency_ms"] += latency_ms
            
            # Step 6: Publish metrics
            await self.publish_metrics(topic, message, latency_ms, success=True)
            
            logger.info(
                "Message processed successfully",
                topic=topic,
                ticket_id=ticket_id,
                conversation_id=conversation_id,
                customer_id=customer_id,
                latency_ms=round(latency_ms, 2)
            )
            
        except Exception as error:
            # Calculate latency even for errors
            latency_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Handle error (apology + DLQ)
            await self.handle_error(topic, message, error)
            
            # Publish error metrics
            await self.publish_metrics(topic, message, latency_ms, success=False)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        avg_latency = (
            self._stats["total_latency_ms"] / self._stats["processed"]
            if self._stats["processed"] > 0 else 0
        )
        
        return {
            **self._stats,
            "avg_latency_ms": round(avg_latency, 2),
        }


# =============================================================================
# Main Entry Point
# =============================================================================

async def main():
    """
    Main async entrypoint for the message processor worker.
    
    Sets up Kafka consumer and starts processing loop.
    """
    logger.info("Starting UnifiedMessageProcessor worker")
    
    # Initialize database pool
    db_pool = await asyncpg.create_pool(
        host="localhost",
        port=5432,
        user="postgres",
        password="postgres",
        database="novasaas",
        min_size=5,
        max_size=20,
    )
    set_db_pool(db_pool)
    
    # Initialize Kafka producer
    producer = create_producer(
        bootstrap_servers="localhost:9092",
        client_id="message-processor-producer",
    )
    await producer.start()
    
    # Initialize Kafka consumer
    consumer = create_consumer(
        bootstrap_servers="localhost:9092",
        group_id="message-processor",
        client_id="message-processor-consumer",
    )
    
    # Create processor
    processor = UnifiedMessageProcessor(
        db_pool=db_pool,
        producer=producer,
    )
    set_kafka_clients(producer, consumer)
    
    # Define message handler
    async def message_handler(topic: str, message: Dict[str, Any]) -> None:
        await processor.process_message(topic, message)
    
    # Define error handler
    async def error_handler(topic: str, message: Dict[str, Any], error: Exception) -> None:
        await processor.handle_error(topic, message, error)
    
    # Start consuming
    await consumer.start(INBOUND_TOPICS)
    
    logger.info(
        "Worker ready, consuming from topics",
        topics=INBOUND_TOPICS
    )
    
    try:
        await consumer.consume(
            handler=message_handler,
            error_handler=error_handler,
        )
    except asyncio.CancelledError:
        logger.info("Worker cancelled")
    finally:
        # Cleanup
        await consumer.stop()
        await producer.stop()
        await db_pool.close()
        
        stats = processor.get_stats()
        logger.info("Worker stopped", stats=stats)


# =============================================================================
# CLI Entry Point
# =============================================================================

if __name__ == "__main__":
    import sys
    
    # Configure logging
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger("INFO"),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=False,
    )
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker interrupted")
        sys.exit(0)
