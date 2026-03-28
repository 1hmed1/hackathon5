"""
NovaSaaS Customer Success AI Agent - Backend API
"""
from contextlib import asynccontextmanager
from typing import Optional, List, Any
from datetime import datetime

import asyncpg
import structlog
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, EmailStr


# Configure structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger("INFO"),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False,
)

logger = structlog.get_logger()

# Global connection pool
db_pool: Optional[asyncpg.Pool] = None


# =============================================================================
# Pydantic Models - Response Schemas
# =============================================================================


class HealthStatus(BaseModel):
    status: str
    database: str
    channels: dict[str, str]


class TicketMessage(BaseModel):
    id: int
    ticket_id: int
    sender: str
    sender_type: str  # "customer" or "agent" or "system"
    message: str
    timestamp: datetime


class Ticket(BaseModel):
    id: int
    customer_id: int
    subject: str
    status: str  # "open", "in_progress", "resolved", "closed"
    priority: str  # "low", "medium", "high", "critical"
    channel: str  # "email", "chat", "phone", "web"
    category: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    assigned_to: Optional[str] = None


class TicketDetail(Ticket):
    messages: List[TicketMessage] = []


class Customer(BaseModel):
    id: int
    name: str
    email: str
    company: Optional[str] = None
    created_at: datetime
    channel_identifiers: dict[str, Optional[str]] = Field(
        default_factory=dict,
        description="Channel-specific IDs: email, chat_id, phone, etc.",
    )


class Conversation(BaseModel):
    id: int
    customer_id: int
    customer_name: str
    customer_email: str
    channel: str
    status: str
    last_message_at: datetime
    message_count: int


class MetricsOverview(BaseModel):
    total_tickets: int
    open_tickets: int
    escalations: int
    avg_sentiment: float
    tickets_by_channel: dict[str, int]
    tickets_by_status: dict[str, int]


class ChannelMetrics(BaseModel):
    channel: str
    total_tickets: int
    open_tickets: int
    resolved_tickets: int
    avg_response_time_hours: Optional[float] = None
    avg_sentiment: Optional[float] = None


class SupportSubmission(BaseModel):
    name: str
    email: EmailStr
    subject: str
    category: str
    message: str
    priority: str = Field(default="medium", description="low, medium, high, critical")


class SupportSubmissionResponse(BaseModel):
    ticket_id: int
    status: str
    message: str


class PaginatedTickets(BaseModel):
    tickets: List[Ticket]
    total: int
    page: int
    page_size: int
    total_pages: int


class PaginatedConversations(BaseModel):
    conversations: List[Conversation]
    total: int
    page: int
    page_size: int


class PaginatedCustomers(BaseModel):
    customers: List[Customer]
    total: int
    page: int
    page_size: int


# =============================================================================
# Lifespan Events
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events - setup and teardown"""
    global db_pool

    logger.info("Starting NovaSaaS Customer Success API")

    # Startup: Create asyncpg connection pool
    try:
        db_pool = await asyncpg.create_pool(
            host="localhost",
            port=5432,
            user="postgres",
            password="postgres",
            database="novasaas",
            min_size=5,
            max_size=20,
            command_timeout=60,
        )
        logger.info("Database connection pool created successfully")
    except Exception as e:
        logger.error(f"Failed to create database pool: {e}")
        db_pool = None

    yield

    # Shutdown: Close database pool
    if db_pool:
        await db_pool.close()
        logger.info("Database connection pool closed")

    logger.info("Shutting down NovaSaaS Customer Success API")


# =============================================================================
# FastAPI Application
# =============================================================================


app = FastAPI(
    title="NovaSaaS Support",
    description="Customer Success AI System API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware for localhost:3000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# Health Endpoint
# =============================================================================


@app.get("/health", response_model=HealthStatus)
async def health_check():
    """Health check endpoint with database and channel status"""
    db_status = "connected" if db_pool else "disconnected"

    # Check channel health (simulated - would check actual channel connections)
    channels = {
        "email": "healthy",
        "chat": "healthy",
        "phone": "healthy",
        "web": "healthy",
    }

    return HealthStatus(
        status="healthy",
        database=db_status,
        channels=channels,
    )


# =============================================================================
# Tickets Endpoints
# =============================================================================


@app.get("/api/tickets", response_model=PaginatedTickets)
async def list_tickets(
    status: Optional[str] = Query(None, description="Filter by status"),
    channel: Optional[str] = Query(None, description="Filter by channel"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """List all tickets with optional filters and pagination"""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")

    # Build query with filters
    query = """
        SELECT id, customer_id, subject, status, priority, channel, 
               category, created_at, updated_at, assigned_to
        FROM tickets
        WHERE 1=1
    """
    count_query = "SELECT COUNT(*) FROM tickets WHERE 1=1"
    params: List[Any] = []
    count_params: List[Any] = []
    param_index = 1

    if status:
        query += f" AND status = ${param_index}"
        count_query += f" AND status = ${param_index}"
        params.append(status)
        count_params.append(status)
        param_index += 1

    if channel:
        query += f" AND channel = ${param_index}"
        count_query += f" AND channel = ${param_index}"
        params.append(channel)
        count_params.append(channel)
        param_index += 1

    if priority:
        query += f" AND priority = ${param_index}"
        count_query += f" AND priority = ${param_index}"
        params.append(priority)
        count_params.append(priority)
        param_index += 1

    # Add pagination
    offset = (page - 1) * page_size
    query += f" ORDER BY created_at DESC LIMIT ${param_index} OFFSET ${param_index + 1}"
    params.extend([page_size, offset])

    async with db_pool.acquire() as conn:
        # Get total count
        count_result = await conn.fetchval(count_query, *count_params)
        total = count_result or 0

        # Get paginated tickets
        rows = await conn.fetch(query, *params)

    tickets = [
        Ticket(
            id=row["id"],
            customer_id=row["customer_id"],
            subject=row["subject"],
            status=row["status"],
            priority=row["priority"],
            channel=row["channel"],
            category=row["category"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            assigned_to=row["assigned_to"],
        )
        for row in rows
    ]

    total_pages = (total + page_size - 1) // page_size

    return PaginatedTickets(
        tickets=tickets,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@app.get("/api/tickets/{ticket_id}", response_model=TicketDetail)
async def get_ticket(ticket_id: int):
    """Get a single ticket with full message history"""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")

    async with db_pool.acquire() as conn:
        # Get ticket details
        ticket_row = await conn.fetchrow(
            """
            SELECT id, customer_id, subject, status, priority, channel, 
                   category, created_at, updated_at, assigned_to
            FROM tickets
            WHERE id = $1
            """,
            ticket_id,
        )

        if not ticket_row:
            raise HTTPException(status_code=404, detail="Ticket not found")

        # Get message history
        message_rows = await conn.fetch(
            """
            SELECT id, ticket_id, sender, sender_type, message, timestamp
            FROM ticket_messages
            WHERE ticket_id = $1
            ORDER BY timestamp ASC
            """,
            ticket_id,
        )

    ticket = Ticket(
        id=ticket_row["id"],
        customer_id=ticket_row["customer_id"],
        subject=ticket_row["subject"],
        status=ticket_row["status"],
        priority=ticket_row["priority"],
        channel=ticket_row["channel"],
        category=ticket_row["category"],
        created_at=ticket_row["created_at"],
        updated_at=ticket_row["updated_at"],
        assigned_to=ticket_row["assigned_to"],
    )

    messages = [
        TicketMessage(
            id=row["id"],
            ticket_id=row["ticket_id"],
            sender=row["sender"],
            sender_type=row["sender_type"],
            message=row["message"],
            timestamp=row["timestamp"],
        )
        for row in message_rows
    ]

    return TicketDetail(**ticket.model_dump(), messages=messages)


# =============================================================================
# Conversations Endpoint
# =============================================================================


@app.get("/api/conversations", response_model=PaginatedConversations)
async def list_conversations(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """List conversations with customer info"""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")

    offset = (page - 1) * page_size

    async with db_pool.acquire() as conn:
        # Get total count
        total = await conn.fetchval("SELECT COUNT(*) FROM conversations")

        # Get conversations with customer info
        rows = await conn.fetch(
            """
            SELECT 
                c.id,
                c.customer_id,
                cust.name as customer_name,
                cust.email as customer_email,
                c.channel,
                c.status,
                c.last_message_at,
                c.message_count
            FROM conversations c
            JOIN customers cust ON c.customer_id = cust.id
            ORDER BY c.last_message_at DESC
            LIMIT $1 OFFSET $2
            """,
            page_size,
            offset,
        )

    conversations = [
        Conversation(
            id=row["id"],
            customer_id=row["customer_id"],
            customer_name=row["customer_name"],
            customer_email=row["customer_email"],
            channel=row["channel"],
            status=row["status"],
            last_message_at=row["last_message_at"],
            message_count=row["message_count"],
        )
        for row in rows
    ]

    return PaginatedConversations(
        conversations=conversations,
        total=total or 0,
        page=page,
        page_size=page_size,
    )


# =============================================================================
# Customers Endpoint
# =============================================================================


@app.get("/api/customers", response_model=PaginatedCustomers)
async def list_customers(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """List customers with their channel identifiers"""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")

    offset = (page - 1) * page_size

    async with db_pool.acquire() as conn:
        # Get total count
        total = await conn.fetchval("SELECT COUNT(*) FROM customers")

        # Get customers
        rows = await conn.fetch(
            """
            SELECT id, name, email, company, created_at
            FROM customers
            ORDER BY created_at DESC
            LIMIT $1 OFFSET $2
            """,
            page_size,
            offset,
        )

        # Get channel identifiers for each customer
        customers = []
        for row in rows:
            channel_ids = await conn.fetch(
                """
                SELECT channel_type, channel_id
                FROM customer_channel_identifiers
                WHERE customer_id = $1
                """,
                row["id"],
            )

            channel_identifiers = {
                ci["channel_type"]: ci["channel_id"] for ci in channel_ids
            }

            customers.append(
                Customer(
                    id=row["id"],
                    name=row["name"],
                    email=row["email"],
                    company=row["company"],
                    created_at=row["created_at"],
                    channel_identifiers=channel_identifiers,
                )
            )

    return PaginatedCustomers(
        customers=customers,
        total=total or 0,
        page=page,
        page_size=page_size,
    )


# =============================================================================
# Metrics Endpoints
# =============================================================================


@app.get("/api/metrics/overview", response_model=MetricsOverview)
async def get_metrics_overview():
    """
    Get overall metrics:
    - total_tickets, open_tickets, escalations
    - avg_sentiment
    - tickets_by_channel, tickets_by_status
    """
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")

    async with db_pool.acquire() as conn:
        # Get basic counts
        total_tickets = await conn.fetchval("SELECT COUNT(*) FROM tickets")
        open_tickets = await conn.fetchval(
            "SELECT COUNT(*) FROM tickets WHERE status IN ('open', 'in_progress')"
        )
        escalations = await conn.fetchval(
            "SELECT COUNT(*) FROM tickets WHERE priority IN ('high', 'critical') "
            "OR status = 'escalated'"
        )

        # Get average sentiment
        avg_sentiment = await conn.fetchval(
            "SELECT AVG(sentiment_score) FROM ticket_sentiments"
        )
        avg_sentiment = float(avg_sentiment) if avg_sentiment else 0.0

        # Get tickets by channel
        channel_rows = await conn.fetch(
            """
            SELECT channel, COUNT(*) as count
            FROM tickets
            GROUP BY channel
            """
        )
        tickets_by_channel = {row["channel"]: row["count"] for row in channel_rows}

        # Get tickets by status
        status_rows = await conn.fetch(
            """
            SELECT status, COUNT(*) as count
            FROM tickets
            GROUP BY status
            """
        )
        tickets_by_status = {row["status"]: row["count"] for row in status_rows}

    return MetricsOverview(
        total_tickets=total_tickets or 0,
        open_tickets=open_tickets or 0,
        escalations=escalations or 0,
        avg_sentiment=round(avg_sentiment, 2),
        tickets_by_channel=tickets_by_channel,
        tickets_by_status=tickets_by_status,
    )


@app.get("/api/metrics/channels", response_model=List[ChannelMetrics])
async def get_metrics_channels():
    """Get per-channel breakdown of metrics"""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT 
                channel,
                COUNT(*) as total_tickets,
                COUNT(*) FILTER (WHERE status IN ('open', 'in_progress')) as open_tickets,
                COUNT(*) FILTER (WHERE status = 'resolved') as resolved_tickets,
                AVG(EXTRACT(EPOCH FROM (first_response_at - created_at)) / 3600) as avg_response_time_hours,
                AVG(sentiment_score) as avg_sentiment
            FROM tickets
            GROUP BY channel
            ORDER BY total_tickets DESC
            """
        )

    return [
        ChannelMetrics(
            channel=row["channel"],
            total_tickets=row["total_tickets"],
            open_tickets=row["open_tickets"],
            resolved_tickets=row["resolved_tickets"],
            avg_response_time_hours=(
                round(row["avg_response_time_hours"], 2)
                if row["avg_response_time_hours"]
                else None
            ),
            avg_sentiment=(
                round(row["avg_sentiment"], 2) if row["avg_sentiment"] else None
            ),
        )
        for row in rows
    ]


# =============================================================================
# Support Submission Endpoint
# =============================================================================


@app.post("/api/support/submit", response_model=SupportSubmissionResponse)
async def submit_support_form(submission: SupportSubmission):
    """
    Submit a support ticket from the web form.
    
    Required fields:
    - name, email, subject, category, message
    - priority (default: medium)
    """
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database not available")

    async with db_pool.acquire() as conn:
        # Find or create customer
        customer_row = await conn.fetchrow(
            "SELECT id FROM customers WHERE email = $1", submission.email
        )

        if not customer_row:
            # Create new customer
            customer_id = await conn.fetchval(
                """
                INSERT INTO customers (name, email, company, created_at)
                VALUES ($1, $2, $3, NOW())
                RETURNING id
                """,
                submission.name,
                submission.email,
                None,
            )
        else:
            customer_id = customer_row["id"]

        # Create ticket
        ticket_id = await conn.fetchval(
            """
            INSERT INTO tickets (
                customer_id, subject, status, priority, channel, 
                category, created_at, updated_at
            )
            VALUES ($1, $2, 'open', $3, 'web', $4, NOW(), NOW())
            RETURNING id
            """,
            customer_id,
            submission.subject,
            submission.priority,
            submission.category,
        )

        # Add initial message
        await conn.execute(
            """
            INSERT INTO ticket_messages (ticket_id, sender, sender_type, message, timestamp)
            VALUES ($1, $2, 'customer', $3, NOW())
            """,
            ticket_id,
            submission.name,
            submission.message,
        )

    return SupportSubmissionResponse(
        ticket_id=ticket_id,
        status="submitted",
        message="Your support ticket has been created successfully",
    )


# =============================================================================
# Root Endpoint
# =============================================================================


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "service": "NovaSaaS Support",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "tickets": "/api/tickets",
            "conversations": "/api/conversations",
            "customers": "/api/customers",
            "metrics": "/api/metrics",
            "support": "/api/support/submit",
        },
    }
