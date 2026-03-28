"""
Web Form Handler for NovaSaaS Customer Success System

FastAPI router for customer-facing support form submissions.
"""
import structlog
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field, EmailStr, validator

logger = structlog.get_logger()

# Router instance
router = APIRouter(prefix="/support", tags=["support"])

# Kafka producer (initialized externally)
_kafka_producer = None
_kafka_topic = "support_tickets"


def set_kafka_producer(producer, topic: str = "support_tickets") -> None:
    """Set the Kafka producer for the handler"""
    global _kafka_producer, _kafka_topic
    _kafka_producer = producer
    _kafka_topic = topic
    logger.info("Kafka producer set for web form handler", topic=topic)


# =============================================================================
# Pydantic Models
# =============================================================================

class PriorityEnum(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class CategoryEnum(str, Enum):
    technical = "technical"
    billing = "billing"
    feature_request = "feature_request"
    account = "account"
    integration = "integration"
    other = "other"


class SupportSubmission(BaseModel):
    """Request model for support form submission"""
    name: str = Field(..., min_length=1, max_length=255, description="Customer's full name")
    email: EmailStr = Field(..., description="Customer's email address")
    subject: str = Field(..., min_length=5, max_length=500, description="Subject of the support request")
    category: CategoryEnum = Field(..., description="Category of the support request")
    message: str = Field(..., min_length=10, max_length=5000, description="Detailed message")
    priority: PriorityEnum = Field(default=PriorityEnum.medium, description="Requested priority level")
    
    @validator('message')
    def validate_message_length(cls, v):
        if len(v.strip()) < 10:
            raise ValueError("Message must be at least 10 characters")
        return v.strip()
    
    @validator('subject')
    def validate_subject(cls, v):
        if len(v.strip()) < 5:
            raise ValueError("Subject must be at least 5 characters")
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "John Doe",
                "email": "john@example.com",
                "subject": "Unable to login to my account",
                "category": "technical",
                "message": "I have been trying to login for the past hour but keep getting an error message saying 'Invalid credentials'. I have tried resetting my password but the email never arrives.",
                "priority": "high"
            }
        }


class SupportSubmissionResponse(BaseModel):
    """Response model for support form submission"""
    ticket_id: int = Field(..., description="Created ticket ID")
    status: str = Field(default="submitted", description="Submission status")
    message: str = Field(default="Your support ticket has been created successfully", description="Confirmation message")
    estimated_response_time: str = Field(default="2-4 hours", description="Expected response time")
    reference_number: str = Field(..., description="Human-readable reference number")


class TicketStatusResponse(BaseModel):
    """Response model for ticket status check"""
    ticket_id: int = Field(..., description="Ticket ID")
    reference_number: str = Field(..., description="Reference number")
    status: str = Field(..., description="Current ticket status")
    subject: str = Field(..., description="Ticket subject")
    category: str = Field(..., description="Ticket category")
    priority: str = Field(..., description="Ticket priority")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    messages: List[Dict[str, Any]] = Field(default_factory=list, description="Message history")
    estimated_resolution: Optional[str] = Field(None, description="Estimated resolution time")


class TicketNotFoundResponse(BaseModel):
    """Response model for ticket not found"""
    error: str = Field(default="Ticket not found", description="Error message")
    ticket_id: int = Field(..., description="Requested ticket ID")
    suggestions: List[str] = Field(
        default_factory=lambda: [
            "Check the ticket ID and try again",
            "Contact support if you believe this is an error",
        ],
        description="Helpful suggestions"
    )


# =============================================================================
# Helper Functions
# =============================================================================

def generate_reference_number(ticket_id: int) -> str:
    """Generate a human-readable reference number"""
    year = datetime.utcnow().year
    return f"TKT-{year}-{ticket_id:04d}"


async def publish_to_kafka(ticket_data: Dict[str, Any]) -> None:
    """Publish ticket submission to Kafka"""
    if not _kafka_producer:
        logger.warning("Kafka producer not configured, skipping publish")
        return
    
    try:
        from aiokafka import AIOKafkaProducer
        
        producer = _kafka_producer
        await producer.send_and_wait(
            _kafka_topic,
            key=str(ticket_data['ticket_id']).encode(),
            value=str(ticket_data).encode(),
        )
        logger.info(
            "Ticket published to Kafka",
            ticket_id=ticket_data['ticket_id'],
            topic=_kafka_topic
        )
    except Exception as error:
        logger.error("Failed to publish to Kafka", error=str(error))


# =============================================================================
# API Endpoints
# =============================================================================

@router.post("/submit", response_model=SupportSubmissionResponse)
async def submit_support_form(
    submission: SupportSubmission,
    background_tasks: BackgroundTasks,
):
    """
    Submit a support ticket from the web form.
    
    This endpoint:
    1. Validates the submission
    2. Creates a ticket in the database
    3. Publishes to Kafka for async processing
    4. Returns confirmation with ticket ID
    
    **Priority Levels:**
    - `low`: General questions, minor issues
    - `medium`: Non-urgent problems (default)
    - `high`: Important issues affecting work
    - `critical`: System down, data loss
    """
    logger.info(
        "Support form submission received",
        email=submission.email,
        category=submission.category.value,
        priority=submission.priority.value
    )
    
    # Get database pool from app state (injected by FastAPI)
    from fastapi import Request
    # Note: In actual implementation, you'd get the pool from request.app.state
    
    # For now, simulate ticket creation
    # In production, this would insert into the database
    ticket_id = datetime.utcnow().timestamp() % 100000  # Simulated ID
    ticket_id = int(ticket_id)
    
    # Create ticket data for Kafka
    ticket_data = {
        "ticket_id": ticket_id,
        "customer_name": submission.name,
        "customer_email": submission.email,
        "subject": submission.subject,
        "category": submission.category.value,
        "priority": submission.priority.value,
        "message": submission.message,
        "channel": "web_form",
        "status": "open",
        "created_at": datetime.utcnow().isoformat(),
        "reference_number": generate_reference_number(ticket_id),
    }
    
    # Publish to Kafka in background
    background_tasks.add_task(publish_to_kafka, ticket_data)
    
    # Calculate estimated response time based on priority
    response_times = {
        "low": "24-48 hours",
        "medium": "4-8 hours",
        "high": "1-2 hours",
        "critical": "15-30 minutes",
    }
    
    return SupportSubmissionResponse(
        ticket_id=ticket_id,
        status="submitted",
        message="Your support ticket has been created successfully. We will respond shortly.",
        estimated_response_time=response_times.get(submission.priority.value, "2-4 hours"),
        reference_number=generate_reference_number(ticket_id),
    )


@router.get("/ticket/{ticket_id}", response_model=TicketStatusResponse)
async def get_ticket_status(ticket_id: int):
    """
    Get the status of a support ticket.
    
    Use this endpoint for status polling on the customer-facing form.
    Returns the current status, message history, and estimated resolution time.
    """
    logger.info("Ticket status check", ticket_id=ticket_id)
    
    # In production, this would query the database
    # For now, return a simulated response
    
    # Simulate ticket not found for most IDs
    if ticket_id > 1000:
        raise HTTPException(
            status_code=404,
            detail=TicketNotFoundResponse(
                error="Ticket not found",
                ticket_id=ticket_id,
            ).model_dump()
        )
    
    # Simulated ticket data
    return TicketStatusResponse(
        ticket_id=ticket_id,
        reference_number=generate_reference_number(ticket_id),
        status="in_progress",
        subject="Sample ticket subject",
        category="technical",
        priority="medium",
        created_at=datetime.utcnow().isoformat(),
        updated_at=datetime.utcnow().isoformat(),
        messages=[
            {
                "id": 1,
                "sender": "Customer",
                "sender_type": "customer",
                "message": "Original support request message...",
                "timestamp": datetime.utcnow().isoformat(),
            }
        ],
        estimated_resolution="2-4 hours",
    )


@router.get("/ticket/{ticket_id}/messages", response_model=List[Dict[str, Any]])
async def get_ticket_messages(ticket_id: int):
    """
    Get all messages for a ticket.
    
    Returns the complete message history for polling updates.
    """
    logger.info("Ticket messages request", ticket_id=ticket_id)
    
    # Simulated response
    return [
        {
            "id": 1,
            "sender": "Customer",
            "sender_type": "customer",
            "message": "Original support request message...",
            "timestamp": datetime.utcnow().isoformat(),
        }
    ]


@router.post("/ticket/{ticket_id}/message")
async def add_ticket_message(ticket_id: int, message: str, sender: str = "Customer"):
    """
    Add a follow-up message to an existing ticket.
    
    Allows customers to add additional information to their ticket.
    """
    logger.info(
        "Adding ticket message",
        ticket_id=ticket_id,
        sender=sender,
        message_length=len(message)
    )
    
    # In production, this would insert into the database
    
    return {
        "status": "success",
        "message": "Message added successfully",
        "ticket_id": ticket_id,
    }


@router.get("/categories", response_model=List[Dict[str, str]])
async def get_support_categories():
    """
    Get available support categories.
    
    Useful for populating the category dropdown in the form.
    """
    return [
        {"value": "technical", "label": "Technical Issue", "description": "Bugs, errors, technical problems"},
        {"value": "billing", "label": "Billing", "description": "Payments, invoices, subscriptions"},
        {"value": "feature_request", "label": "Feature Request", "description": "Suggestions for new features"},
        {"value": "account", "label": "Account Management", "description": "Login, profile, settings"},
        {"value": "integration", "label": "Integration", "description": "API, webhooks, third-party tools"},
        {"value": "other", "label": "Other", "description": "Anything else"},
    ]


@router.get("/health")
async def health_check():
    """Health check for the support form service"""
    return {
        "status": "healthy",
        "service": "web_form_handler",
        "kafka_connected": _kafka_producer is not None,
        "timestamp": datetime.utcnow().isoformat(),
    }


# =============================================================================
# Router inclusion helper
# =============================================================================

def include_router(app):
    """Include the support router in a FastAPI app"""
    app.include_router(router)
    logger.info("Support form router included in app")


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    "router",
    "include_router",
    "set_kafka_producer",
    "SupportSubmission",
    "SupportSubmissionResponse",
    "TicketStatusResponse",
    "PriorityEnum",
    "CategoryEnum",
]
