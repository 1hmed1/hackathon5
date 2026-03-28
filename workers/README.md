# NovaSaaS Workers

Kafka workers for async message processing in the NovaSaaS Customer Success system.

## Installation

```bash
pip install -r requirements.txt
```

## Workers

### Message Processor (`message_processor.py`)

Unified processor for all inbound messages from Kafka.

**Consumes from:**
- `fte.tickets.incoming`
- `fte.channels.email.inbound`
- `fte.channels.whatsapp.inbound`
- `fte.channels.webform.inbound`

**Pipeline:**
1. **Resolve Customer** - Find or create customer by email/phone
2. **Get/Create Conversation** - Reuse active conversation within 24h
3. **Store Inbound Message** - Save to `ticket_messages` table
4. **Run AI Agent** - Generate response using customer_success_agent
5. **Store Outbound Response** - Save agent response
6. **Publish Metrics** - Send metrics to `fte.metrics` topic

**Error Handling:**
- Sends apology via original channel
- Publishes failed messages to `fte.dlq` (Dead Letter Queue)
- Logs structured errors with full context

## Usage

### Run the Message Processor

```bash
cd workers
python message_processor.py
```

### Programmatic Usage

```python
import asyncio
import asyncpg
from message_processor import UnifiedMessageProcessor
from kafka_client import create_producer, create_consumer

async def main():
    # Setup
    db_pool = await asyncpg.create_pool("postgresql://...")
    producer = create_producer()
    await producer.start()
    
    processor = UnifiedMessageProcessor(
        db_pool=db_pool,
        producer=producer,
    )
    
    # Process a message directly
    message = {
        "channel": "email",
        "customer_email": "user@example.com",
        "content": "Help me!",
        "subject": "Urgent issue",
    }
    
    await processor.process_message("fte.tickets.incoming", message)
    
    # Get stats
    stats = processor.get_stats()
    print(f"Processed: {stats['processed']}")
    print(f"Avg latency: {stats['avg_latency_ms']}ms")
    
    # Cleanup
    await producer.stop()
    await db_pool.close()

asyncio.run(main())
```

## UnifiedMessageProcessor Methods

| Method | Description |
|--------|-------------|
| `resolve_customer(message)` | Find/create customer by email or phone |
| `get_or_create_conversation(customer_id, channel)` | Get active conversation (within 24h) or create new |
| `store_message(conversation_id, message, sender_type)` | Store message in database |
| `run_agent(ticket_id, message)` | Run AI agent for response |
| `store_outbound(ticket_id, response, channel)` | Store agent response |
| `publish_metrics(topic, message, latency_ms, success)` | Publish to metrics topic |
| `handle_error(topic, message, error)` | Send apology + publish to DLQ |
| `process_message(topic, message)` | Full pipeline processing |
| `get_stats()` | Get processing statistics |

## Kafka Topics

### Inbound (Consumed)
- `fte.tickets.incoming` - General ticket submissions
- `fte.channels.email.inbound` - Gmail messages
- `fte.channels.whatsapp.inbound` - WhatsApp messages
- `fte.channels.webform.inbound` - Web form submissions

### Outbound (Published)
- `fte.metrics` - Processing metrics
- `fte.dlq` - Failed messages (Dead Letter Queue)

## Message Format

### Inbound Message
```python
{
    "channel": "email",  # or "whatsapp", "web_form"
    "customer_email": "user@example.com",
    "customer_phone": None,  # or "+1234567890"
    "customer_name": "John Doe",
    "content": "Message body...",
    "subject": "Support request",
    "channel_message_id": "provider-specific-id",
    "received_at": "2024-01-15T10:30:00Z",
    "metadata": {...}
}
```

### Metrics Event
```python
{
    "event_type": "message_processed",
    "source_topic": "fte.channels.email.inbound",
    "channel": "email",
    "customer_id": 123,
    "ticket_id": 456,
    "conversation_id": 789,
    "latency_ms": 245.67,
    "timestamp": "2024-01-15T10:30:00Z",
    "success": True
}
```

### DLQ Event
```python
{
    "original_topic": "fte.channels.email.inbound",
    "original_message": {...},
    "error": "Database connection failed",
    "error_type": "PostgresError",
    "failed_at": "2024-01-15T10:30:00Z"
}
```

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/novasaas

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_CONSUMER_GROUP=message-processor

# Logging
LOG_LEVEL=INFO
```

## Processing Statistics

The processor tracks:
- `processed`: Total messages processed successfully
- `errors`: Total processing errors
- `total_latency_ms`: Cumulative processing time
- `avg_latency_ms`: Average processing latency

Access via `processor.get_stats()`.

## File Structure

```
workers/
├── __init__.py
├── message_processor.py    # Unified message processor
└── README.md              # This file
```
