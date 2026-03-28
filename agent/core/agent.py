"""
NovaSaaS Customer Success AI Agent - Core Module
"""
import structlog
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

logger = structlog.get_logger()


class Priority(str, Enum):
    P1 = "p1"
    P2 = "p2"
    P3 = "p3"
    P4 = "p4"


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_CUSTOMER = "waiting_customer"
    RESOLVED = "resolved"
    CLOSED = "closed"


@dataclass
class TicketContext:
    """Context information for a support ticket"""
    ticket_id: str
    customer_id: str
    customer_tier: str
    subject: str
    description: str
    current_priority: Priority
    current_status: TicketStatus
    conversation_history: List[Dict[str, Any]]
    customer_health_score: Optional[int] = None
    open_tickets_count: Optional[int] = None


@dataclass
class AgentDecision:
    """Decision made by the AI agent"""
    action: str  # classify, escalate, respond, route, etc.
    priority: Optional[Priority] = None
    assignee: Optional[str] = None
    response: Optional[str] = None
    escalation_reason: Optional[str] = None
    confidence: float = 0.0
    metadata: Optional[Dict[str, Any]] = None


class CustomerSuccessAgent:
    """
    Main AI Agent for Customer Success operations
    
    This agent analyzes support tickets, classifies priority,
    determines escalation needs, and routes to appropriate teams.
    """
    
    def __init__(self, model_provider: str = "openai"):
        self.model_provider = model_provider
        self.context_files = {
            "company_profile": "context/company-profile.md",
            "product_docs": "context/product-docs.md",
            "escalation_rules": "context/escalation-rules.md",
            "brand_voice": "context/brand-voice.md"
        }
        logger.info("CustomerSuccessAgent initialized", model_provider=model_provider)
    
    async def analyze_ticket(self, context: TicketContext) -> AgentDecision:
        """
        Analyze a support ticket and return a decision
        
        Args:
            context: TicketContext with all relevant information
            
        Returns:
            AgentDecision with recommended actions
        """
        logger.info(
            "Analyzing ticket",
            ticket_id=context.ticket_id,
            customer_tier=context.customer_tier
        )
        
        # Load context documents
        system_prompt = await self._build_system_prompt()
        
        # Build analysis prompt
        analysis_prompt = self._build_analysis_prompt(context)
        
        # Call LLM (placeholder - actual implementation would call OpenAI/Anthropic)
        # response = await self._call_llm(system_prompt, analysis_prompt)
        
        # Parse response and return decision
        return AgentDecision(
            action="classify",
            priority=Priority.P3,
            confidence=0.85,
            metadata={"model_used": self.model_provider}
        )
    
    async def _build_system_prompt(self) -> str:
        """Build the system prompt from context documents"""
        # Load and combine context files
        prompt_parts = [
            "You are NovaSaaS Customer Success AI Agent.",
            "You help classify, route, and respond to customer support tickets.",
            "Follow the escalation rules and brand voice guidelines."
        ]
        return "\n".join(prompt_parts)
    
    def _build_analysis_prompt(self, context: TicketContext) -> str:
        """Build the analysis prompt for a specific ticket"""
        return f"""
Analyze this support ticket:

Ticket ID: {context.ticket_id}
Customer: {context.customer_id} ({context.customer_tier})
Subject: {context.subject}
Description: {context.description}
Current Priority: {context.current_priority}
Status: {context.current_status}
Health Score: {context.customer_health_score}
Open Tickets: {context.open_tickets_count}

Determine:
1. Correct priority (P1-P4)
2. If escalation is needed
3. Appropriate response or routing
"""
    
    async def check_escalation_needed(self, context: TicketContext) -> tuple[bool, str]:
        """
        Check if a ticket requires escalation
        
        Returns:
            Tuple of (needs_escalation, reason)
        """
        # P1 always escalates
        if context.current_priority == Priority.P1:
            return True, "P1 Critical severity"
        
        # Enterprise customers with P2 escalate
        if context.customer_tier == "enterprise" and context.current_priority == Priority.P2:
            return True, "Enterprise customer P2"
        
        # Check for escalation keywords in conversation
        escalation_keywords = ["cancel", "churn", "lawyer", "legal", "competitor"]
        for message in context.conversation_history:
            text = message.get("content", "").lower()
            for keyword in escalation_keywords:
                if keyword in text:
                    return True, f"Escalation keyword detected: {keyword}"
        
        return False, ""


# Export main classes
__all__ = ["CustomerSuccessAgent", "TicketContext", "AgentDecision", "Priority", "TicketStatus"]
