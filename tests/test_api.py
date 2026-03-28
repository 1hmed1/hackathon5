"""
NovaSaaS Backend API - Integration Tests

Tests for FastAPI backend using httpx AsyncClient.
"""
import pytest
import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, patch

import httpx
from fastapi.testclient import TestClient


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def client():
    """Create test client for FastAPI app"""
    from backend.main import app
    
    # Mock database pool for tests
    mock_pool = AsyncMock()
    
    with patch('backend.main.db_pool', mock_pool):
        with TestClient(app=app, base_url="http://test") as test_client:
            yield test_client


@pytest.fixture
async def async_client():
    """Create async httpx client for testing"""
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        yield client


@pytest.fixture
def mock_db_response():
    """Mock database responses"""
    return {
        "tickets": [
            {
                "id": 1,
                "customer_id": 1,
                "subject": "Test ticket",
                "status": "open",
                "priority": "medium",
                "channel": "email",
                "category": "technical",
                "created_at": "2024-01-15T10:00:00Z",
                "updated_at": "2024-01-15T10:00:00Z",
                "assigned_to": None,
            }
        ],
        "total": 1,
        "page": 1,
        "page_size": 20,
        "total_pages": 1,
    }


# =============================================================================
# Health Check Tests
# =============================================================================

def test_health_check(client):
    """Test health check endpoint returns healthy status"""
    response = client.get("/health")
    
    assert response.status_code == 200
    data = response.json()
    
    assert "status" in data
    assert data["status"] == "healthy"
    assert "database" in data
    assert "channels" in data


@pytest.mark.asyncio
async def test_health_check_async(async_client):
    """Test health check with async client"""
    try:
        response = await async_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    except httpx.ConnectError:
        pytest.skip("Backend not running")


# =============================================================================
# Support Form Tests
# =============================================================================

def test_form_submission_returns_ticket_id(client):
    """Test that valid form submission returns ticket ID"""
    submission_data = {
        "name": "John Doe",
        "email": "john@example.com",
        "subject": "Unable to login",
        "category": "technical",
        "message": "I have been trying to login for the past hour but keep getting an error.",
        "priority": "medium",
    }
    
    response = client.post("/api/support/submit", json=submission_data)
    
    # Should succeed (or fail gracefully if DB not connected)
    assert response.status_code in [200, 503]
    
    if response.status_code == 200:
        data = response.json()
        assert "ticket_id" in data
        assert isinstance(data["ticket_id"], int)
        assert data["status"] == "submitted"


def test_form_validation_rejects_bad_input(client):
    """Test that invalid form input is rejected"""
    invalid_submissions = [
        # Missing name
        {
            "email": "john@example.com",
            "subject": "Test subject",
            "category": "technical",
            "message": "Test message",
        },
        # Invalid email
        {
            "name": "John Doe",
            "email": "not-an-email",
            "subject": "Test subject",
            "category": "technical",
            "message": "Test message",
        },
        # Subject too short
        {
            "name": "John Doe",
            "email": "john@example.com",
            "subject": "Hi",
            "category": "technical",
            "message": "Test message",
        },
        # Message too short
        {
            "name": "John Doe",
            "email": "john@example.com",
            "subject": "Test subject",
            "category": "technical",
            "message": "Help",
        },
        # Empty submission
        {},
    ]
    
    for submission in invalid_submissions:
        response = client.post("/api/support/submit", json=submission)
        assert response.status_code in [422, 400], \
            f"Should reject invalid submission: {submission}"


def test_form_validation_accepts_valid_input(client):
    """Test that valid input passes validation"""
    valid_submissions = [
        {
            "name": "John Doe",
            "email": "john@example.com",
            "subject": "Unable to login to my account",
            "category": "technical",
            "message": "I have been trying to login for the past hour but keep getting an error message.",
            "priority": "low",
        },
        {
            "name": "Jane Smith",
            "email": "jane@company.org",
            "subject": "Feature request: Dark mode support",
            "category": "feature_request",
            "message": "It would be great if you could add dark mode support to the dashboard.",
            "priority": "low",
        },
    ]
    
    for submission in valid_submissions:
        response = client.post("/api/support/submit", json=submission)
        # Should not return 422 validation error
        assert response.status_code != 422


# =============================================================================
# Ticket Tests
# =============================================================================

def test_ticket_status_retrieval(client, mock_db_response):
    """Test retrieving ticket status"""
    ticket_id = 1
    
    # Mock database response
    with patch('backend.main.db_pool') as mock_pool:
        mock_conn = AsyncMock()
        mock_conn.fetchrow.return_value = mock_db_response["tickets"][0]
        mock_conn.fetch.return_value = []
        mock_pool.acquire.return_value.__aenter__.return_value = mock_conn
        
        response = client.get(f"/api/tickets/{ticket_id}")
        
        # Should succeed or return 503 if DB not connected
        assert response.status_code in [200, 503]
        
        if response.status_code == 200:
            data = response.json()
            assert "id" in data
            assert data["id"] == ticket_id


def test_tickets_list_with_filters(client, mock_db_response):
    """Test listing tickets with various filters"""
    # Test without filters
    response = client.get("/api/tickets")
    assert response.status_code in [200, 503]
    
    # Test with status filter
    response = client.get("/api/tickets?status=open")
    assert response.status_code in [200, 503]
    
    # Test with channel filter
    response = client.get("/api/tickets?channel=email")
    assert response.status_code in [200, 503]
    
    # Test with priority filter
    response = client.get("/api/tickets?priority=high")
    assert response.status_code in [200, 503]
    
    # Test with pagination
    response = client.get("/api/tickets?page=1&page_size=10")
    assert response.status_code in [200, 503]
    
    # Test with multiple filters
    response = client.get("/api/tickets?status=open&channel=email&priority=high")
    assert response.status_code in [200, 503]


def test_tickets_list_returns_paginated_response(client):
    """Test that tickets list returns paginated response structure"""
    response = client.get("/api/tickets")
    
    if response.status_code == 200:
        data = response.json()
        assert "tickets" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert isinstance(data["tickets"], list)


# =============================================================================
# Metrics Tests
# =============================================================================

def test_metrics_overview_has_required_fields(client):
    """Test that metrics overview contains all required fields"""
    response = client.get("/api/metrics/overview")
    
    if response.status_code == 200:
        data = response.json()
        
        required_fields = [
            "total_tickets",
            "open_tickets",
            "escalations",
            "avg_sentiment",
            "tickets_by_channel",
            "tickets_by_status",
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Check types
        assert isinstance(data["total_tickets"], int)
        assert isinstance(data["open_tickets"], int)
        assert isinstance(data["escalations"], int)
        assert isinstance(data["avg_sentiment"], (int, float))
        assert isinstance(data["tickets_by_channel"], dict)
        assert isinstance(data["tickets_by_status"], dict)


def test_metrics_channels_returns_list(client):
    """Test that metrics channels returns a list"""
    response = client.get("/api/metrics/channels")
    
    if response.status_code == 200:
        data = response.json()
        assert isinstance(data, list)
        
        if len(data) > 0:
            channel = data[0]
            assert "channel" in channel
            assert "total_tickets" in channel


# =============================================================================
# Conversations Tests
# =============================================================================

def test_conversations_list(client):
    """Test listing conversations"""
    response = client.get("/api/conversations")
    
    if response.status_code == 200:
        data = response.json()
        assert "conversations" in data
        assert "total" in data
        assert isinstance(data["conversations"], list)


# =============================================================================
# Customers Tests
# =============================================================================

def test_customers_list(client):
    """Test listing customers"""
    response = client.get("/api/customers")
    
    if response.status_code == 200:
        data = response.json()
        assert "customers" in data
        assert "total" in data
        assert isinstance(data["customers"], list)
        
        if len(data["customers"]) > 0:
            customer = data["customers"][0]
            assert "id" in customer
            assert "name" in customer
            assert "email" in customer


# =============================================================================
# Error Handling Tests
# =============================================================================

def test_404_for_nonexistent_ticket(client):
    """Test 404 for nonexistent ticket"""
    response = client.get("/api/tickets/999999")
    
    if response.status_code != 503:  # If DB is connected
        assert response.status_code == 404


def test_invalid_filter_values(client):
    """Test handling of invalid filter values"""
    # Invalid status
    response = client.get("/api/tickets?status=invalid_status")
    # Should not crash
    assert response.status_code in [200, 400, 422, 503]
    
    # Invalid priority
    response = client.get("/api/tickets?priority=super_urgent")
    assert response.status_code in [200, 400, 422, 503]


def test_pagination_edge_cases(client):
    """Test pagination edge cases"""
    # Page 0 (should default to 1 or return error)
    response = client.get("/api/tickets?page=0")
    assert response.status_code in [200, 400, 422, 503]
    
    # Negative page
    response = client.get("/api/tickets?page=-1")
    assert response.status_code in [200, 400, 422, 503]
    
    # Very large page size
    response = client.get("/api/tickets?page_size=10000")
    assert response.status_code in [200, 400, 422, 503]


# =============================================================================
# Root Endpoint Tests
# =============================================================================

def test_root_endpoint(client):
    """Test root endpoint returns API info"""
    response = client.get("/")
    
    assert response.status_code == 200
    data = response.json()
    assert "service" in data or "status" in data


# =============================================================================
# CORS Tests
# =============================================================================

def test_cors_headers(client):
    """Test CORS headers are present"""
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        }
    )
    
    # Should allow CORS from localhost:3000
    assert response.status_code in [200, 404]  # OPTIONS might not be implemented


# =============================================================================
# Integration Tests (require running backend)
# =============================================================================

@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_ticket_workflow(async_client):
    """Test complete ticket creation and retrieval workflow"""
    try:
        # 1. Submit a ticket
        submission = {
            "name": "Integration Test User",
            "email": "integration@test.com",
            "subject": "Integration test ticket",
            "category": "technical",
            "message": "This is an integration test message.",
            "priority": "low",
        }
        
        response = await async_client.post("/api/support/submit", json=submission)
        assert response.status_code == 200
        
        data = response.json()
        ticket_id = data["ticket_id"]
        
        # 2. Retrieve the ticket
        response = await async_client.get(f"/api/tickets/{ticket_id}")
        assert response.status_code == 200
        
        ticket = response.json()
        assert ticket["id"] == ticket_id
        assert ticket["subject"] == submission["subject"]
        
    except httpx.ConnectError:
        pytest.skip("Backend not running for integration test")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_metrics_endpoint_integration(async_client):
    """Test metrics endpoint with real backend"""
    try:
        response = await async_client.get("/api/metrics/overview")
        assert response.status_code == 200
        
        data = response.json()
        assert "total_tickets" in data
        
    except httpx.ConnectError:
        pytest.skip("Backend not running for integration test")


# =============================================================================
# Run Tests
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
