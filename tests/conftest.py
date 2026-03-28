"""
NovaSaaS Test Configuration

Pytest configuration and shared fixtures.
"""
import os
import sys
import pytest
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def pytest_configure(config):
    """Configure pytest markers"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires running services)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "requires_db: mark test as requiring database connection"
    )
    config.addinivalue_line(
        "markers", "requires_kafka: mark test as requiring Kafka connection"
    )
    config.addinivalue_line(
        "markers", "requires_openai: mark test as requiring OpenAI API key"
    )


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests"""
    import asyncio
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_config():
    """Test configuration"""
    return {
        "backend_url": os.getenv("TEST_BACKEND_URL", "http://localhost:8000"),
        "frontend_url": os.getenv("TEST_FRONTEND_URL", "http://localhost:3000"),
        "database_url": os.getenv("TEST_DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/novasaas_test"),
        "kafka_servers": os.getenv("TEST_KAFKA_SERVERS", "localhost:9092"),
    }
