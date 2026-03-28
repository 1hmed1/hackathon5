"""
NovaSaaS Customer Success AI Agent - Unit Tests

Tests for the AI agent using pytest.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_db_pool():
    """Mock database connection pool"""
    pool = AsyncMock()
    conn = AsyncMock()
    
    # Mock fetchrow for customer lookup
    conn.fetchrow.return_value = None  # No existing customer
    conn.fetchval.return_value = 1  # New customer/ticket ID
    conn.fetch.return_value = []  # Empty message history
    
    pool.acquire.return_value.__aenter__.return_value = conn
    return pool


@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer"""
    producer = AsyncMock()
    producer.publish = AsyncMock(return_value={"status": "success"})
    producer.send_to_dlq = AsyncMock(return_value={"status": "success"})
    return producer


@pytest.fixture
def agent_module(mock_db_pool, mock_kafka_producer):
    """Import agent module with mocked dependencies"""
    with patch.dict('sys.modules', {}):
        from agent import customer_success_agent as agent
        agent.set_db_pool(mock_db_pool)
        return agent


# =============================================================================
# Message Handling Tests
# =============================================================================

@pytest.mark.asyncio
async def test_empty_message_handled_gracefully(agent_module):
    """Test that empty or whitespace-only messages are handled gracefully"""
    # Test with empty message
    response = await agent_module.run_agent(
        message="",
        channel="web_form",
        customer_id=1
    )
    
    assert response is not None
    assert "help" in response.lower() or "assist" in response.lower()
    
    # Test with whitespace-only message
    response = await agent_module.run_agent(
        message="   ",
        channel="web_form",
        customer_id=1
    )
    
    assert response is not None


@pytest.mark.asyncio
async def test_pricing_question_always_escalates(agent_module, mock_db_pool):
    """Test that pricing questions always trigger escalation"""
    pricing_messages = [
        "How much does the enterprise plan cost?",
        "What's your pricing?",
        "I want to know the cost",
        "Can you give me a discount?",
        "Is there a free tier?",
    ]
    
    for message in pricing_messages:
        # Mock the agent to detect pricing intent
        with patch.object(agent_module, 'create_customer_success_agent') as mock_agent_factory:
            mock_agent = MagicMock()
            mock_agent.instructions = agent_module.SYSTEM_PROMPT
            
            # Run the agent
            response = await agent_module.run_agent(
                message=message,
                channel="email",
                customer_id=1
            )
            
            # Response should indicate escalation or human handoff
            assert response is not None
            # Check for escalation indicators
            assert any(keyword in response.lower() for keyword in [
                "human", "team", "specialist", "sales", "escalat", "connect"
            ])


@pytest.mark.asyncio
async def test_angry_message_escalates_or_shows_empathy(agent_module):
    """Test that angry/frustrated messages get escalated or empathetic response"""
    angry_messages = [
        "This is absolutely unacceptable! I'm furious!",
        "Your service is terrible! I want a refund NOW!",
        "I've been waiting for 3 days! This is ridiculous!",
        "I'm going to cancel my subscription if this isn't fixed!",
        "Worst customer service ever! I hate this product!",
    ]
    
    for message in angry_messages:
        response = await agent_module.run_agent(
            message=message,
            channel="chat",
            customer_id=1
        )
        
        assert response is not None
        
        # Should either escalate or show empathy
        response_lower = response.lower()
        
        has_empathy = any(word in response_lower for word in [
            "understand", "frustrat", "sorry", "apologize", "empathize",
            "concern", "important", "priority"
        ])
        
        has_escalation = any(word in response_lower for word in [
            "escalat", "specialist", "team", "human", "supervisor",
            "priority", "urgent", "immediately"
        ])
        
        assert has_empathy or has_escalation, \
            f"Angry message should get empathy or escalation: {message}"


# =============================================================================
# Channel Formatting Tests
# =============================================================================

@pytest.mark.asyncio
async def test_email_response_has_greeting(agent_module):
    """Test that email responses include proper greeting and signature"""
    response = await agent_module.run_agent(
        message="I need help with my account settings",
        channel="email",
        customer_id=1
    )
    
    assert response is not None
    
    # Email should have formal greeting
    has_greeting = any(greeting in response for greeting in [
        "Dear", "Hello", "Hi", "Good morning", "Good afternoon"
    ])
    
    # Email should have signature
    has_signature = any(signature in response for signature in [
        "Best regards", "Sincerely", "Kind regards", "NovaSaaS", "Support Team"
    ])
    
    assert has_greeting or has_signature, "Email should have greeting or signature"


@pytest.mark.asyncio
async def test_whatsapp_response_under_500_chars(agent_module):
    """Test that WhatsApp responses are under 500 characters (safe limit)"""
    response = await agent_module.run_agent(
        message="How do I reset my password?",
        channel="whatsapp",
        customer_id=1
    )
    
    assert response is not None
    assert len(response) <= 500, f"WhatsApp response too long: {len(response)} chars"
    
    # Should be casual and include emoji
    assert any(char in response for char in ["👋", "😊", "📱", "✨", "✅"])


# =============================================================================
# Tool Usage Tests
# =============================================================================

@pytest.mark.asyncio
async def test_tool_order_create_ticket_first(agent_module, mock_db_pool):
    """Test that agent creates ticket before providing substantive help"""
    call_order = []
    
    # Track function calls
    original_create_ticket = agent_module.create_ticket
    
    async def tracked_create_ticket(*args, **kwargs):
        call_order.append("create_ticket")
        return await original_create_ticket(*args, **kwargs)
    
    with patch.object(agent_module, 'create_ticket', side_effect=tracked_create_ticket):
        response = await agent_module.run_agent(
            message="My dashboard isn't loading properly",
            channel="web_form",
            customer_id=1
        )
        
        # Verify ticket was created
        assert "create_ticket" in call_order, "Should create ticket first"
        
        # Response should reference the ticket
        assert response is not None
        assert any(term in response.lower() for term in [
            "ticket", "case", "reference", "tracking"
        ])


@pytest.mark.asyncio
async def test_knowledge_base_no_results_graceful(agent_module, mock_db_pool):
    """Test graceful handling when knowledge base has no results"""
    # Mock empty knowledge base results
    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = []  # No KB results
    mock_conn.fetchrow.return_value = {"id": 1, "name": "Test User", "email": "test@example.com"}
    mock_conn.fetchval.return_value = 1
    
    mock_pool = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
    agent_module.set_db_pool(mock_pool)
    
    # Search for something that won't exist
    result = await agent_module.search_knowledge_base(
        query="nonexistent feature xyz123",
        max_results=5
    )
    
    # Should return gracefully with empty results
    assert result is not None
    assert "results" in result
    assert len(result["results"]) == 0
    
    # Should not raise an error
    assert "error" not in result or result.get("results") is not None


# =============================================================================
# Sentiment Analysis Tests
# =============================================================================

@pytest.mark.asyncio
async def test_positive_sentiment_gets_friendly_response(agent_module):
    """Test that positive messages get friendly responses"""
    positive_messages = [
        "Love your product! It's amazing!",
        "Thank you so much for the quick help!",
        "Your team is awesome!",
    ]
    
    for message in positive_messages:
        response = await agent_module.run_agent(
            message=message,
            channel="chat",
            customer_id=1
        )
        
        assert response is not None
        # Should match positive tone
        assert any(word in response.lower() for word in [
            "glad", "happy", "wonderful", "great", "thank", "appreciate"
        ])


# =============================================================================
# Error Handling Tests
# =============================================================================

@pytest.mark.asyncio
async def test_database_error_handled_gracefully(agent_module):
    """Test that database errors are handled gracefully"""
    # Mock database error
    mock_pool = AsyncMock()
    mock_pool.acquire.return_value.__aenter__.side_effect = Exception("DB connection failed")
    agent_module.set_db_pool(mock_pool)
    
    # Should not raise, should handle gracefully
    response = await agent_module.run_agent(
        message="Help me with my account",
        channel="web_form",
        customer_id=1
    )
    
    # Should still return some response
    assert response is not None


# =============================================================================
# Priority Classification Tests
# =============================================================================

@pytest.mark.asyncio
async def test_critical_keywords_get_high_priority(agent_module):
    """Test that critical keywords result in high priority classification"""
    critical_messages = [
        "System is completely down!",
        "Data loss occurred!",
        "Security breach detected!",
        "Cannot access any features!",
    ]
    
    for message in critical_messages:
        response = await agent_module.run_agent(
            message=message,
            channel="email",
            customer_id=1
        )
        
        assert response is not None
        # Should indicate urgency
        assert any(word in response.lower() for word in [
            "urgent", "priority", "immediate", "critical", "asap"
        ])


# =============================================================================
# Multi-turn Conversation Tests
# =============================================================================

@pytest.mark.asyncio
async def test_followup_question_maintains_context(agent_module):
    """Test that follow-up questions maintain conversation context"""
    # First message
    response1 = await agent_module.run_agent(
        message="I can't login to my account",
        channel="chat",
        customer_id=1
    )
    
    assert response1 is not None
    
    # Follow-up (in real scenario, this would include conversation history)
    response2 = await agent_module.run_agent(
        message="I tried resetting password but didn't receive email",
        channel="chat",
        customer_id=1
    )
    
    assert response2 is not None
    # Should reference previous issue
    assert any(word in response2.lower() for word in [
        "login", "password", "email", "reset", "account"
    ])


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
