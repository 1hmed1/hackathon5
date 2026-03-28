"""
NovaSaaS Customer Success AI Agent
Uses OpenAI Agents SDK with function tools for customer support operations.
"""
import asyncio
import asyncpg
import structlog
from typing import Optional, List, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field, EmailStr
from agents import Agent, function_tool, Runner

logger = structlog.get_logger()

# Database connection pool (initialized externally)
_db_pool: Optional[asyncpg.Pool] = None


def set_db_pool(pool: asyncpg.Pool) -> None:
    """Set the database connection pool for the agent"""
    global _db_pool
    _db_pool = pool
    logger.info("Database pool set for agent")


# =============================================================================
# Pydantic Input Models for Tools
# =============================================================================


class SearchKnowledgeBaseInput(BaseModel):
    query: str = Field(..., description="The search query to find relevant knowledge base articles")
    max_results: int = Field(default=5, ge=1, le=20, description="Maximum number of results to return")


class CreateTicketInput(BaseModel):
    customer_id: int = Field(..., description="The ID of the customer creating the ticket")
    issue: str = Field(..., description="Description of the issue or request")
    priority: str = Field(..., description="Priority level: low, medium, high, critical")
    channel: str = Field(..., description="Channel through which the ticket was created: email, whatsapp, web_form, chat, phone")
    subject: Optional[str] = Field(default=None, description="Optional subject line for the ticket")
    category: Optional[str] = Field(default=None, description="Optional category for the ticket")


class GetCustomerHistoryInput(BaseModel):
    customer_id: int = Field(..., description="The ID of the customer to get history for")


class EscalateToHumanInput(BaseModel):
    ticket_id: int = Field(..., description="The ID of the ticket to escalate")
    reason: str = Field(..., description="Reason for escalation")
    urgency: str = Field(..., description="Urgency level: low, medium, high, critical")


class SendResponseInput(BaseModel):
    ticket_id: int = Field(..., description="The ID of the ticket to respond to")
    message: str = Field(..., description="The response message content")
    channel: str = Field(..., description="Channel to send response through: email, whatsapp, web_form, chat, phone")


# =============================================================================
# Function Tools
# =============================================================================


@function_tool
async def search_knowledge_base(query: str, max_results: int = 5) -> Dict[str, Any]:
    """
    Search the knowledge base for relevant articles using text search.
    
    Args:
        query: The search query to find relevant knowledge base articles
        max_results: Maximum number of results to return (default: 5)
    
    Returns:
        Dictionary containing search results with articles and relevance scores
    """
    logger.info("Searching knowledge base", query=query, max_results=max_results)
    
    if not _db_pool:
        return {"error": "Database not connected", "results": []}
    
    try:
        async with _db_pool.acquire() as conn:
            # Use PostgreSQL full-text search
            rows = await conn.fetch(
                """
                SELECT id, title, content, category, tags,
                       ts_rank(to_tsvector('english', title || ' ' || content), plainto_tsquery('english', $1)) as relevance
                FROM knowledge_base
                WHERE to_tsvector('english', title || ' ' || content) @@ plainto_tsquery('english', $1)
                ORDER BY relevance DESC
                LIMIT $2
                """,
                query,
                max_results
            )
            
            results = [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "content": row["content"][:500] + "..." if len(row["content"]) > 500 else row["content"],
                    "category": row["category"],
                    "tags": row["tags"],
                    "relevance": float(row["relevance"])
                }
                for row in rows
            ]
            
            logger.info("Knowledge base search completed", results_count=len(results))
            return {"query": query, "results": results, "total_found": len(results)}
            
    except Exception as e:
        logger.error("Knowledge base search failed", error=str(e))
        return {"error": str(e), "results": []}


@function_tool
async def create_ticket(
    customer_id: int,
    issue: str,
    priority: str,
    channel: str,
    subject: Optional[str] = None,
    category: Optional[str] = None
) -> Dict[str, Any]:
    """
    Create a new support ticket in the system.
    
    Args:
        customer_id: The ID of the customer creating the ticket
        issue: Description of the issue or request
        priority: Priority level (low, medium, high, critical)
        channel: Channel through which the ticket was created
        subject: Optional subject line for the ticket
        category: Optional category for the ticket
    
    Returns:
        Dictionary containing the created ticket ID and details
    """
    logger.info(
        "Creating ticket",
        customer_id=customer_id,
        priority=priority,
        channel=channel
    )
    
    if not _db_pool:
        return {"error": "Database not connected"}
    
    try:
        async with _db_pool.acquire() as conn:
            # Generate subject from issue if not provided
            if not subject:
                subject = issue[:100] + "..." if len(issue) > 100 else issue
            
            # Create the ticket
            ticket_id = await conn.fetchval(
                """
                INSERT INTO tickets (
                    customer_id, subject, description, status, priority, 
                    channel, category, created_at, updated_at
                )
                VALUES ($1, $2, $3, 'open', $4, $5, $6, NOW(), NOW())
                RETURNING id
                """,
                customer_id,
                subject,
                issue,
                priority,
                channel,
                category
            )
            
            # Create initial message
            await conn.execute(
                """
                INSERT INTO ticket_messages (ticket_id, sender, sender_type, message, timestamp)
                VALUES ($1, 'Customer', 'customer', $2, NOW())
                """,
                ticket_id,
                issue
            )
            
            logger.info("Ticket created successfully", ticket_id=ticket_id)
            return {
                "ticket_id": ticket_id,
                "customer_id": customer_id,
                "subject": subject,
                "status": "open",
                "priority": priority,
                "channel": channel,
                "category": category,
                "created_at": datetime.utcnow().isoformat()
            }
            
    except Exception as e:
        logger.error("Failed to create ticket", error=str(e))
        return {"error": str(e)}


@function_tool
async def get_customer_history(customer_id: int) -> Dict[str, Any]:
    """
    Get the last 20 messages across ALL channels for a customer.
    
    Args:
        customer_id: The ID of the customer to get history for
    
    Returns:
        Dictionary containing customer info and message history
    """
    logger.info("Getting customer history", customer_id=customer_id)
    
    if not _db_pool:
        return {"error": "Database not connected"}
    
    try:
        async with _db_pool.acquire() as conn:
            # Get customer info
            customer = await conn.fetchrow(
                """
                SELECT id, name, email, company, created_at
                FROM customers
                WHERE id = $1
                """,
                customer_id
            )
            
            if not customer:
                return {"error": f"Customer {customer_id} not found"}
            
            # Get message history across all channels (last 20)
            messages = await conn.fetch(
                """
                SELECT 
                    tm.id,
                    tm.ticket_id,
                    t.subject,
                    t.channel,
                    tm.sender,
                    tm.sender_type,
                    tm.message,
                    tm.timestamp
                FROM ticket_messages tm
                JOIN tickets t ON tm.ticket_id = t.id
                WHERE t.customer_id = $1
                ORDER BY tm.timestamp DESC
                LIMIT 20
                """,
                customer_id
            )
            
            # Get ticket count
            ticket_count = await conn.fetchval(
                "SELECT COUNT(*) FROM tickets WHERE customer_id = $1",
                customer_id
            )
            
            history = [
                {
                    "id": row["id"],
                    "ticket_id": row["ticket_id"],
                    "subject": row["subject"],
                    "channel": row["channel"],
                    "sender": row["sender"],
                    "sender_type": row["sender_type"],
                    "message": row["message"],
                    "timestamp": row["timestamp"].isoformat()
                }
                for row in messages
            ]
            
            logger.info("Customer history retrieved", message_count=len(history))
            return {
                "customer": {
                    "id": customer["id"],
                    "name": customer["name"],
                    "email": customer["email"],
                    "company": customer["company"],
                    "customer_since": customer["created_at"].isoformat()
                },
                "total_tickets": ticket_count,
                "recent_messages": history,
                "message_count": len(history)
            }
            
    except Exception as e:
        logger.error("Failed to get customer history", error=str(e))
        return {"error": str(e)}


@function_tool
async def escalate_to_human(ticket_id: int, reason: str, urgency: str) -> Dict[str, Any]:
    """
    Escalate a ticket to human support.
    
    Args:
        ticket_id: The ID of the ticket to escalate
        reason: Reason for escalation
        urgency: Urgency level (low, medium, high, critical)
    
    Returns:
        Dictionary containing escalation status and details
    """
    logger.info(
        "Escalating ticket",
        ticket_id=ticket_id,
        reason=reason,
        urgency=urgency
    )
    
    if not _db_pool:
        return {"error": "Database not connected"}
    
    try:
        async with _db_pool.acquire() as conn:
            # Check if ticket exists
            ticket = await conn.fetchrow(
                "SELECT id, status FROM tickets WHERE id = $1",
                ticket_id
            )
            
            if not ticket:
                return {"error": f"Ticket {ticket_id} not found"}
            
            # Update ticket status
            await conn.execute(
                """
                UPDATE tickets
                SET status = 'escalated',
                    priority = CASE 
                        WHEN $1 = 'critical' THEN 'critical'
                        WHEN $1 = 'high' THEN 'high'
                        ELSE priority
                    END,
                    updated_at = NOW()
                WHERE id = $2
                """,
                urgency,
                ticket_id
            )
            
            # Add escalation note
            await conn.execute(
                """
                INSERT INTO ticket_messages (ticket_id, sender, sender_type, message, timestamp)
                VALUES ($1, 'System', 'system', $2, NOW())
                """,
                ticket_id,
                f"🚨 ESCALATED to human support.\nReason: {reason}\nUrgency: {urgency}"
            )
            
            logger.info("Ticket escalated successfully", ticket_id=ticket_id)
            return {
                "ticket_id": ticket_id,
                "status": "escalated",
                "urgency": urgency,
                "reason": reason,
                "escalated_at": datetime.utcnow().isoformat(),
                "message": f"Ticket #{ticket_id} has been escalated with {urgency} urgency"
            }
            
    except Exception as e:
        logger.error("Failed to escalate ticket", error=str(e))
        return {"error": str(e)}


@function_tool
async def send_response(ticket_id: int, message: str, channel: str) -> Dict[str, Any]:
    """
    Send a response to a ticket, formatted appropriately for the channel.
    
    Channel formatting rules:
    - email: formal greeting + signature + full detail
    - whatsapp: under 300 chars, casual, end with 📱 tip
    - web_form: semi-formal, clean
    
    Args:
        ticket_id: The ID of the ticket to respond to
        message: The response message content
        channel: Channel to send response through (email, whatsapp, web_form, chat, phone)
    
    Returns:
        Dictionary containing the formatted message and send status
    """
    logger.info(
        "Sending response",
        ticket_id=ticket_id,
        channel=channel,
        message_length=len(message)
    )
    
    if not _db_pool:
        return {"error": "Database not connected"}
    
    try:
        async with _db_pool.acquire() as conn:
            # Get ticket and customer info
            ticket = await conn.fetchrow(
                """
                SELECT t.*, c.name as customer_name, c.email as customer_email
                FROM tickets t
                JOIN customers c ON t.customer_id = c.id
                WHERE t.id = $1
                """,
                ticket_id
            )
            
            if not ticket:
                return {"error": f"Ticket {ticket_id} not found"}
            
            # Format message based on channel
            formatted_message = _format_message_for_channel(
                message,
                channel,
                customer_name=ticket["customer_name"]
            )
            
            # Store response in database
            await conn.execute(
                """
                INSERT INTO ticket_messages (ticket_id, sender, sender_type, message, timestamp)
                VALUES ($1, 'Support Agent', 'agent', $2, NOW())
                """,
                ticket_id,
                formatted_message
            )
            
            # Update ticket status if it was waiting for response
            if ticket["status"] == "open":
                await conn.execute(
                    """
                    UPDATE tickets
                    SET status = 'in_progress', updated_at = NOW()
                    WHERE id = $1
                    """,
                    ticket_id
                )
            
            logger.info("Response sent successfully", ticket_id=ticket_id)
            return {
                "ticket_id": ticket_id,
                "channel": channel,
                "formatted_message": formatted_message,
                "sent_at": datetime.utcnow().isoformat(),
                "status": "sent"
            }
            
    except Exception as e:
        logger.error("Failed to send response", error=str(e))
        return {"error": str(e)}


def _format_message_for_channel(message: str, channel: str, customer_name: str = "valued customer") -> str:
    """Format a message according to channel-specific rules"""
    
    if channel == "email":
        # Formal greeting + signature + full detail
        return f"""Dear {customer_name},

Thank you for contacting NovaSaaS Support.

{message}

If you have any further questions or concerns, please don't hesitate to reach out.

Best regards,
NovaSaaS Customer Success Team
support@novasaas.com
"""
    
    elif channel == "whatsapp":
        # Under 300 chars, casual, end with 📱 tip
        truncated = message[:250] + "..." if len(message) > 250 else message
        return f"""Hi {customer_name}! 👋 

{truncated}

Need more help? Just reply to this message! 📱"""
    
    elif channel == "web_form":
        # Semi-formal, clean
        return f"""Hello {customer_name},

{message}

Thank you for choosing NovaSaaS.

—
NovaSaaS Support Team"""
    
    elif channel == "chat":
        # Conversational, friendly
        return f"""Hi {customer_name}! 

{message}

Anything else I can help you with? 😊"""
    
    else:
        # Default/phone - professional
        return f"""Hello {customer_name},

{message}

Thank you for contacting NovaSaaS Support."""


# =============================================================================
# Agent Definition
# =============================================================================


SYSTEM_PROMPT = """You are the NovaSaaS Customer Success AI Agent, an intelligent assistant helping customers with support requests.

## Core Principles

1. **ALWAYS create a ticket first** before providing any substantive help
2. **NEVER discuss pricing** - escalate pricing questions to human sales team
3. **NEVER promise unconfirmed features** - only discuss documented features
4. **Escalate angry customers** - if sentiment appears negative (< 0.3), escalate to human
5. **Adapt tone per channel** - match the communication style to the channel

## Channel Tone Guidelines

- **email**: Professional, detailed, formal greeting and signature
- **whatsapp**: Casual, concise (under 300 chars), friendly emojis, end with 📱
- **web_form**: Semi-formal, clean formatting, helpful but not overly casual
- **chat**: Conversational, friendly, quick responses
- **phone**: Professional, empathetic, clear and articulate

## Escalation Triggers

Escalate to human support when:
- Customer mentions "cancel", "churn", "competitor", "refund", "lawsuit", "legal"
- Sentiment appears angry or frustrated (sentiment < 0.3)
- Pricing or billing disputes
- Feature requests not in documentation
- P1/Critical issues (system down, data loss, security breach)
- Enterprise customers with urgent issues

## Response Process

1. Analyze the customer's message for sentiment and intent
2. Create a ticket using create_ticket() with appropriate priority
3. Search knowledge base if technical question
4. Provide helpful response using send_response() with channel-appropriate formatting
5. Escalate if any escalation triggers are present

## Available Tools

- search_knowledge_base(query, max_results): Find relevant help articles
- create_ticket(customer_id, issue, priority, channel): Create support ticket
- get_customer_history(customer_id): View customer's past interactions
- escalate_to_human(ticket_id, reason, urgency): Escalate to human support
- send_response(ticket_id, message, channel): Send formatted response

## Priority Guidelines

- **critical**: System down, data loss, security breach, payment failure
- **high**: Major feature broken, significant impact on work
- **medium**: Non-critical issues, workarounds available
- **low**: Questions, feature requests, minor issues

Remember: Be helpful, empathetic, and efficient. When in doubt, escalate."""


def create_customer_success_agent() -> Agent:
    """Create and configure the Customer Success AI Agent"""
    
    return Agent(
        name="NovaSaaS Customer Success Agent",
        instructions=SYSTEM_PROMPT,
        tools=[
            search_knowledge_base,
            create_ticket,
            get_customer_history,
            escalate_to_human,
            send_response,
        ],
        model="gpt-4o",
    )


async def run_agent(message: str, channel: str = "web_form", customer_id: int = 1) -> str:
    """
    Run the agent with a customer message.
    
    Args:
        message: The customer's message
        channel: The channel the message came from
        customer_id: The customer's ID
    
    Returns:
        The agent's response
    """
    agent = create_customer_success_agent()
    
    # Build the user prompt
    user_prompt = f"""A customer has sent the following message via {channel}:

Customer ID: {customer_id}
Channel: {channel}
Message: "{message}"

Please help this customer by:
1. Creating a ticket for this interaction
2. Providing a helpful response appropriate for the {channel} channel"""

    result = await Runner.run(agent, user_prompt)
    return result.final_output


# =============================================================================
# Exports
# =============================================================================


__all__ = [
    "set_db_pool",
    "search_knowledge_base",
    "create_ticket",
    "get_customer_history",
    "escalate_to_human",
    "send_response",
    "create_customer_success_agent",
    "run_agent",
    "SYSTEM_PROMPT",
]
