"""
NovaSaaS Customer Success AI Agent - Backend API (SQLite Version)
Quick setup version - uses SQLite instead of PostgreSQL for testing
"""
from contextlib import asynccontextmanager
from typing import Optional, List, Any
from datetime import datetime
import asyncio

import aiosqlite
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

# Global database connection
db_connection: Optional[aiosqlite.Connection] = None


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
    sender_type: str
    message: str
    timestamp: str


class Ticket(BaseModel):
    id: int
    customer_id: int
    subject: str
    status: str
    priority: str
    channel: str
    category: Optional[str] = None
    created_at: str
    updated_at: str
    assigned_to: Optional[str] = None


class TicketDetail(Ticket):
    messages: List[TicketMessage] = []


class Customer(BaseModel):
    id: int
    name: str
    email: str
    company: Optional[str] = None
    created_at: str
    channel_identifiers: dict[str, Optional[str]] = Field(default_factory=dict)


class Conversation(BaseModel):
    id: int
    customer_id: int
    customer_name: str
    customer_email: str
    channel: str
    status: str
    last_message_at: str
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
    priority: str = Field(default="medium")


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
# Database Initialization
# =============================================================================

async def init_database():
    """Initialize SQLite database with schema"""
    global db_connection
    
    db_connection = await aiosqlite.connect("novasaas.db")
    db_connection.row_factory = aiosqlite.Row
    
    # Create tables
    await db_connection.executescript("""
    -- Customers Table
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE,
        company VARCHAR(255),
        tier VARCHAR(50) DEFAULT 'standard',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Customer Channel Identifiers
    CREATE TABLE IF NOT EXISTS customer_channel_identifiers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
        channel_type VARCHAR(50) NOT NULL,
        channel_id VARCHAR(255) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(customer_id, channel_type)
    );

    -- Tickets Table
    CREATE TABLE IF NOT EXISTS tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
        subject VARCHAR(500) NOT NULL,
        description TEXT,
        status VARCHAR(50) DEFAULT 'open',
        priority VARCHAR(50) DEFAULT 'medium',
        channel VARCHAR(50) NOT NULL,
        category VARCHAR(100),
        assigned_to VARCHAR(255),
        first_response_at TIMESTAMP,
        resolved_at TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Ticket Messages Table
    CREATE TABLE IF NOT EXISTS ticket_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER REFERENCES tickets(id) ON DELETE CASCADE,
        sender VARCHAR(255) NOT NULL,
        sender_type VARCHAR(50) NOT NULL,
        message TEXT NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Knowledge Base Table
    CREATE TABLE IF NOT EXISTS knowledge_base (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title VARCHAR(500) NOT NULL,
        content TEXT NOT NULL,
        category VARCHAR(100),
        tags TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Ticket Sentiments Table
    CREATE TABLE IF NOT EXISTS ticket_sentiments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER REFERENCES tickets(id) ON DELETE CASCADE,
        sentiment_score FLOAT,
        analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Conversations Table
    CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
        channel VARCHAR(50) NOT NULL,
        status VARCHAR(50) DEFAULT 'active',
        last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        message_count INTEGER DEFAULT 0
    );

    -- Channel Configurations Table
    CREATE TABLE IF NOT EXISTS channel_configurations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        channel_type VARCHAR(50) UNIQUE NOT NULL,
        config TEXT DEFAULT '{}',
        enabled BOOLEAN DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    -- Metrics Snapshots Table
    CREATE TABLE IF NOT EXISTS metrics_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_date DATE DEFAULT CURRENT_DATE,
        metric_name VARCHAR(100) NOT NULL,
        metric_value FLOAT NOT NULL,
        metadata TEXT DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(snapshot_date, metric_name)
    );

    -- Escalations Table
    CREATE TABLE IF NOT EXISTS escalations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_id INTEGER REFERENCES tickets(id) ON DELETE CASCADE,
        reason TEXT NOT NULL,
        urgency VARCHAR(50) NOT NULL,
        escalated_to VARCHAR(255),
        status VARCHAR(50) DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        resolved_at TIMESTAMP
    );

    -- Insert sample data
    INSERT OR IGNORE INTO customers (name, email, company, tier) VALUES
        ('John Doe', 'john@example.com', 'Acme Corp', 'enterprise'),
        ('Jane Smith', 'jane@example.com', 'StartupXYZ', 'premium'),
        ('Bob Wilson', 'bob@example.com', 'Small Biz LLC', 'standard');

    INSERT OR IGNORE INTO channel_configurations (channel_type, config, enabled) VALUES
        ('email', '{}', 1),
        ('whatsapp', '{}', 1),
        ('web_form', '{}', 1);

    INSERT OR IGNORE INTO knowledge_base (title, content, category, tags) VALUES
        ('How to Reset Your Password', 'To reset your password, go to the login page and click Forgot Password.', 'Account', 'password,login,account'),
        ('Setting Up Two-Factor Authentication', 'To enable 2FA: Go to Settings > Security and click Enable 2FA.', 'Security', '2fa,security,authentication');
    """)
    
    await db_connection.commit()
    logger.info("SQLite database initialized successfully")


# =============================================================================
# Lifespan Events
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events - setup and teardown"""
    global db_connection

    logger.info("Starting NovaSaaS Customer Success API (SQLite version)")

    # Startup: Initialize SQLite database
    try:
        await init_database()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        db_connection = None

    yield

    # Shutdown: Close database connection
    if db_connection:
        await db_connection.close()
        logger.info("Database connection closed")

    logger.info("Shutting down NovaSaaS Customer Success API")


# =============================================================================
# FastAPI Application
# =============================================================================


app = FastAPI(
    title="NovaSaaS Support (SQLite)",
    description="Customer Success AI System API - SQLite Version for Testing",
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
    db_status = "connected" if db_connection else "disconnected"

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
    status: Optional[str] = Query(None),
    channel: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List all tickets with optional filters and pagination"""
    if not db_connection:
        raise HTTPException(status_code=503, detail="Database not available")

    # Build query
    query = """
        SELECT id, customer_id, subject, status, priority, channel,
               category, created_at, updated_at, assigned_to
        FROM tickets
        WHERE 1=1
    """
    count_query = "SELECT COUNT(*) FROM tickets WHERE 1=1"
    params: List[Any] = []
    count_params: List[Any] = []

    if status:
        query += " AND status = ?"
        count_query += " AND status = ?"
        params.append(status)
        count_params.append(status)

    if channel:
        query += " AND channel = ?"
        count_query += " AND channel = ?"
        params.append(channel)
        count_params.append(channel)

    if priority:
        query += " AND priority = ?"
        count_query += " AND priority = ?"
        params.append(priority)
        count_params.append(priority)

    offset = (page - 1) * page_size
    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([page_size, offset])

    # Get total count
    async with db_connection.execute(count_query, count_params) as cursor:
        result = await cursor.fetchone()
        total = result[0] if result else 0

    # Get tickets
    async with db_connection.execute(query, params) as cursor:
        rows = await cursor.fetchall()

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

    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

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
    if not db_connection:
        raise HTTPException(status_code=503, detail="Database not available")

    # Get ticket
    async with db_connection.execute(
        """
        SELECT id, customer_id, subject, status, priority, channel,
               category, created_at, updated_at, assigned_to
        FROM tickets
        WHERE id = ?
        """,
        (ticket_id,),
    ) as cursor:
        ticket_row = await cursor.fetchone()

    if not ticket_row:
        raise HTTPException(status_code=404, detail="Ticket not found")

    # Get messages
    async with db_connection.execute(
        """
        SELECT id, ticket_id, sender, sender_type, message, timestamp
        FROM ticket_messages
        WHERE ticket_id = ?
        ORDER BY timestamp ASC
        """,
        (ticket_id,),
    ) as cursor:
        message_rows = await cursor.fetchall()

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
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List conversations with customer info"""
    if not db_connection:
        raise HTTPException(status_code=503, detail="Database not available")

    offset = (page - 1) * page_size

    # Get total count
    async with db_connection.execute("SELECT COUNT(*) FROM conversations") as cursor:
        result = await cursor.fetchone()
        total = result[0] if result else 0

    # Get conversations
    async with db_connection.execute(
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
        LEFT JOIN customers cust ON c.customer_id = cust.id
        ORDER BY c.last_message_at DESC
        LIMIT ? OFFSET ?
        """,
        (page_size, offset),
    ) as cursor:
        rows = await cursor.fetchall()

    conversations = [
        Conversation(
            id=row["id"],
            customer_id=row["customer_id"],
            customer_name=row["customer_name"] or "Unknown",
            customer_email=row["customer_email"] or "",
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
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    """List customers with their channel identifiers"""
    if not db_connection:
        raise HTTPException(status_code=503, detail="Database not available")

    offset = (page - 1) * page_size

    # Get total count
    async with db_connection.execute("SELECT COUNT(*) FROM customers") as cursor:
        result = await cursor.fetchone()
        total = result[0] if result else 0

    async with db_connection.execute(
        """
        SELECT id, name, email, company, created_at
        FROM customers
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?
        """,
        (page_size, offset),
    ) as cursor:
        rows = await cursor.fetchall()

    customers = []
    for row in rows:
        async with db_connection.execute(
            """
            SELECT channel_type, channel_id
            FROM customer_channel_identifiers
            WHERE customer_id = ?
            """,
            (row["id"],),
        ) as cursor:
            channel_ids = await cursor.fetchall()

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
    """Get overall metrics"""
    if not db_connection:
        raise HTTPException(status_code=503, detail="Database not available")

    async with db_connection.execute("SELECT COUNT(*) FROM tickets") as cursor:
        result = await cursor.fetchone()
        total_tickets = result[0] if result else 0

    async with db_connection.execute(
        "SELECT COUNT(*) FROM tickets WHERE status IN ('open', 'in_progress')"
    ) as cursor:
        result = await cursor.fetchone()
        open_tickets = result[0] if result else 0

    async with db_connection.execute(
        "SELECT COUNT(*) FROM tickets WHERE priority IN ('high', 'critical')"
    ) as cursor:
        result = await cursor.fetchone()
        escalations = result[0] if result else 0

    async with db_connection.execute(
        "SELECT AVG(sentiment_score) FROM ticket_sentiments"
    ) as cursor:
        result = await cursor.fetchone()
        avg_sentiment = float(result[0]) if result and result[0] else 0.0

    async with db_connection.execute(
        "SELECT channel, COUNT(*) as count FROM tickets GROUP BY channel"
    ) as cursor:
        rows = await cursor.fetchall()
        tickets_by_channel = {row["channel"]: row["count"] for row in rows}

    async with db_connection.execute(
        "SELECT status, COUNT(*) as count FROM tickets GROUP BY status"
    ) as cursor:
        rows = await cursor.fetchall()
        tickets_by_status = {row["status"]: row["count"] for row in rows}

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
    if not db_connection:
        raise HTTPException(status_code=503, detail="Database not available")

    async with db_connection.execute(
        """
        SELECT
            channel,
            COUNT(*) as total_tickets,
            COUNT(*) FILTER (WHERE status IN ('open', 'in_progress')) as open_tickets,
            COUNT(*) FILTER (WHERE status = 'resolved') as resolved_tickets
        FROM tickets
        GROUP BY channel
        ORDER BY total_tickets DESC
        """
    ) as cursor:
        rows = await cursor.fetchall()

    return [
        ChannelMetrics(
            channel=row["channel"],
            total_tickets=row["total_tickets"],
            open_tickets=row["open_tickets"],
            resolved_tickets=row["resolved_tickets"],
            avg_response_time_hours=None,
            avg_sentiment=None,
        )
        for row in rows
    ]


# =============================================================================
# Support Submission Endpoint
# =============================================================================


@app.post("/api/support/submit", response_model=SupportSubmissionResponse)
async def submit_support_form(submission: SupportSubmission):
    """Submit a support ticket from the web form."""
    if not db_connection:
        raise HTTPException(status_code=503, detail="Database not available")

    # Find or create customer
    async with db_connection.execute(
        "SELECT id FROM customers WHERE email = ?", (submission.email,)
    ) as cursor:
        customer_row = await cursor.fetchone()

    if not customer_row:
        # Create new customer
        cursor = await db_connection.execute(
            """
            INSERT INTO customers (name, email, company, created_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """,
            (submission.name, submission.email, None),
        )
        customer_id = cursor.lastrowid
        await db_connection.commit()

        # Add channel identifier
        await db_connection.execute(
            """
            INSERT INTO customer_channel_identifiers (customer_id, channel_type, channel_id)
            VALUES (?, 'email', ?)
            """,
            (customer_id, submission.email),
        )
        await db_connection.commit()
    else:
        customer_id = customer_row["id"]

    # Create ticket
    cursor = await db_connection.execute(
        """
        INSERT INTO tickets (
            customer_id, subject, status, priority, channel,
            category, created_at, updated_at
        )
        VALUES (?, ?, 'open', ?, 'web', ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        """,
        (customer_id, submission.subject, submission.priority, submission.category),
    )
    ticket_id = cursor.lastrowid
    await db_connection.commit()

    # Add initial message
    await db_connection.execute(
        """
        INSERT INTO ticket_messages (ticket_id, sender, sender_type, message, timestamp)
        VALUES (?, ?, 'customer', ?, CURRENT_TIMESTAMP)
        """,
        (ticket_id, submission.name, submission.message),
    )
    await db_connection.commit()

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
        "service": "NovaSaaS Support (SQLite)",
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
