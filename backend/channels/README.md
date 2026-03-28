# Channel Handlers

Multi-channel communication handlers for NovaSaaS Customer Success System.

## Overview

This package provides handlers for three communication channels:

| Channel | Handler | Description |
|---------|---------|-------------|
| Email | `GmailHandler` | Gmail API with push notifications |
| WhatsApp | `WhatsAppHandler` | Twilio WhatsApp Business API |
| Web Form | `web_form_handler` | FastAPI router for customer form |

## Installation

```bash
pip install -r requirements.txt
```

Additional dependencies:
- `google-api-python-client` - Gmail API
- `google-auth` - OAuth2 authentication
- `twilio` - WhatsApp messaging

## Gmail Handler

### Setup

```python
from channels import create_gmail_handler

handler = create_gmail_handler(
    service_account_file="path/to/service-account.json",
    delegated_user="support@novasaas.com",
    project_id="my-gcp-project",
    topic_name="gmail-notifications",
)
```

### Push Notifications

```python
# Set up push notifications
result = handler.setup_push_notifications()
print(f"History ID: {result['history_id']}")
```

### Process Incoming Emails

```python
# Process Pub/Sub notification
messages = handler.process_notification(pubsub_message)

# Or get a specific message
message = handler.get_message("message_id")
# Returns normalized dict with channel='email'
```

### Send Replies

```python
result = handler.send_reply(
    to_email="customer@example.com",
    subject="Re: Your ticket",
    body="Hello! We've received your request...",
    thread_id="thread_id"  # Optional for threading
)
```

### Normalized Message Format

```python
{
    "channel": "email",
    "customer_email": "customer@example.com",
    "customer_name": "John Doe",
    "customer_phone": None,
    "content": "Email body text...",
    "subject": "Support request",
    "channel_message_id": "gmail_message_id",
    "channel_thread_id": "gmail_thread_id",
    "received_at": "2024-01-15T10:30:00Z",
    "metadata": {
        "to": "support@novasaas.com",
        "from_raw": "John Doe <customer@example.com>",
        "references": "...",
        "in_reply_to": "...",
        "attachments": [...],
        "label_ids": ["INBOX", "UNREAD"],
    }
}
```

## WhatsApp Handler

### Setup

```python
from channels import create_whatsapp_handler

handler = create_whatsapp_handler(
    account_sid="ACxxxxxxxx",
    auth_token="your-auth-token",
    whatsapp_number="whatsapp:+14155238886",
    webhook_url="https://novasaas.com/webhooks/whatsapp",
)
```

### Webhook Validation

```python
from fastapi import Request

@app.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request):
    if not handler.validate_webhook(request):
        raise HTTPException(status_code=403, detail="Invalid signature")
    
    form_data = await request.form()
    message = handler.process_webhook(dict(form_data))
    
    if message:
        # Process the message
        pass
    
    return Response(status_code=200)
```

### Send Messages

```python
# Text message
result = handler.send_message(
    to_phone="+1234567890",
    body="Hello! Your ticket has been updated."
)

# Media message
result = handler.send_media_message(
    to_phone="+1234567890",
    media_url="https://example.com/image.png",
    caption="Here's a screenshot..."
)
```

### Response Formatting

The handler automatically formats responses for WhatsApp:
- Truncates at 1600 characters
- Splits on sentence boundaries
- Adds ellipsis for truncated messages

```python
formatted = handler.format_response(long_text)
```

### Normalized Message Format

```python
{
    "channel": "whatsapp",
    "customer_email": None,
    "customer_phone": "+1234567890",
    "customer_name": None,
    "content": "Message text...",
    "subject": None,
    "channel_message_id": "SMxxxxxxxx",
    "channel_thread_id": "whatsapp:+1234567890",
    "received_at": "2024-01-15T10:30:00Z",
    "metadata": {
        "from_number": "whatsapp:+1234567890",
        "to_number": "whatsapp:+14155238886",
        "num_media": 0,
        "media": [],
        "message_status": "received",
        "direction": "inbound",
    }
}
```

## Web Form Handler

### Setup

```python
from fastapi import FastAPI
from channels import include_router, set_kafka_producer

app = FastAPI()

# Configure Kafka (optional)
from aiokafka import AIOKafkaProducer
producer = AIOKafkaProducer(bootstrap_servers="localhost:9092")
await producer.start()
set_kafka_producer(producer, "support_tickets")

# Include the router
include_router(app)
```

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/support/submit` | Submit a new ticket |
| GET | `/support/ticket/{id}` | Get ticket status |
| GET | `/support/ticket/{id}/messages` | Get message history |
| POST | `/support/ticket/{id}/message` | Add follow-up message |
| GET | `/support/categories` | List categories |
| GET | `/support/health` | Health check |

### Submit a Ticket

```python
import httpx

response = httpx.post(
    "http://localhost:8000/support/submit",
    json={
        "name": "John Doe",
        "email": "john@example.com",
        "subject": "Unable to login",
        "category": "technical",
        "message": "I've tried resetting my password but...",
        "priority": "high"
    }
)

result = response.json()
print(f"Ticket ID: {result['ticket_id']}")
print(f"Reference: {result['reference_number']}")
```

### Response Format

```json
{
    "ticket_id": 12345,
    "status": "submitted",
    "message": "Your support ticket has been created successfully...",
    "estimated_response_time": "1-2 hours",
    "reference_number": "TKT-2024-0123"
}
```

### Polling for Status

```python
response = httpx.get("http://localhost:8000/support/ticket/12345")
status = response.json()

print(f"Status: {status['status']}")
print(f"Messages: {len(status['messages'])}")
```

## Kafka Integration

The web form handler publishes submissions to Kafka for async processing:

```python
# Message key: ticket_id
# Message value: JSON-encoded ticket data
# Topic: support_tickets (configurable)
```

The agent can consume from this topic to process tickets automatically.

## Environment Variables

```bash
# Gmail
GMAIL_SERVICE_ACCOUNT_FILE=path/to/service-account.json
GMAIL_DELEGATED_USER=support@novasaas.com
GCP_PROJECT_ID=my-project
GMAIL_TOPIC_NAME=gmail-notifications

# WhatsApp
TWILIO_ACCOUNT_SID=ACxxxxxxxx
TWILIO_AUTH_TOKEN=your-token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
TWILIO_WEBHOOK_URL=https://novasaas.com/webhooks/whatsapp

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=support_tickets
```

## File Structure

```
backend/channels/
├── __init__.py
├── gmail_handler.py      # Gmail API handler
├── whatsapp_handler.py   # Twilio WhatsApp handler
└── web_form_handler.py   # FastAPI router
```
