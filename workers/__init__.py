"""
NovaSaaS Customer Success - Workers

Kafka workers for async message processing.
"""

from .message_processor import UnifiedMessageProcessor, main

__all__ = [
    "UnifiedMessageProcessor",
    "main",
]
