"""
NovaSaaS Customer Success - Channel Handlers

Handlers for multiple communication channels:
- Gmail (email)
- WhatsApp (via Twilio)
- Web Form (customer-facing)
"""

from .gmail_handler import GmailHandler, create_gmail_handler
from .whatsapp_handler import WhatsAppHandler, create_whatsapp_handler, create_whatsapp_webhook_handler
from .web_form_handler import (
    router as support_router,
    include_router,
    set_kafka_producer,
    SupportSubmission,
    SupportSubmissionResponse,
    TicketStatusResponse,
    PriorityEnum,
    CategoryEnum,
)

__all__ = [
    # Gmail
    "GmailHandler",
    "create_gmail_handler",
    # WhatsApp
    "WhatsAppHandler",
    "create_whatsapp_handler",
    "create_whatsapp_webhook_handler",
    # Web Form
    "support_router",
    "include_router",
    "set_kafka_producer",
    "SupportSubmission",
    "SupportSubmissionResponse",
    "TicketStatusResponse",
    "PriorityEnum",
    "CategoryEnum",
]
