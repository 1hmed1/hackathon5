#!/usr/bin/env python3
"""
Kafka Topics Initialization Script

Creates all required Kafka topics for NovaSaaS Customer Success system.
"""
import asyncio
import structlog
from aiokafka.admin import AIOKafkaAdminClient, NewTopic

from kafka_client import KafkaTopics, ALL_TOPICS

logger = structlog.get_logger()


# Topic configurations
TOPIC_CONFIGS = {
    # High-volume topics with more partitions
    KafkaTopics.METRICS.value: NewTopic(
        name=KafkaTopics.METRICS.value,
        num_partitions=3,
        replication_factor=1,
    ),
    KafkaTopics.AGENT_REQUESTS.value: NewTopic(
        name=KafkaTopics.AGENT_REQUESTS.value,
        num_partitions=3,
        replication_factor=1,
    ),
    KafkaTopics.AGENT_RESPONSES.value: NewTopic(
        name=KafkaTopics.AGENT_RESPONSES.value,
        num_partitions=3,
        replication_factor=1,
    ),
    
    # Standard topics
    KafkaTopics.TICKETS_INCOMING.value: NewTopic(
        name=KafkaTopics.TICKETS_INCOMING.value,
        num_partitions=1,
        replication_factor=1,
    ),
    KafkaTopics.TICKETS_CREATED.value: NewTopic(
        name=KafkaTopics.TICKETS_CREATED.value,
        num_partitions=1,
        replication_factor=1,
    ),
    KafkaTopics.TICKETS_UPDATED.value: NewTopic(
        name=KafkaTopics.TICKETS_UPDATED.value,
        num_partitions=1,
        replication_factor=1,
    ),
    KafkaTopics.TICKETS_RESOLVED.value: NewTopic(
        name=KafkaTopics.TICKETS_RESOLVED.value,
        num_partitions=1,
        replication_factor=1,
    ),
    
    # Channel topics
    KafkaTopics.CHANNELS_EMAIL_INBOUND.value: NewTopic(
        name=KafkaTopics.CHANNELS_EMAIL_INBOUND.value,
        num_partitions=1,
        replication_factor=1,
    ),
    KafkaTopics.CHANNELS_WHATSAPP_INBOUND.value: NewTopic(
        name=KafkaTopics.CHANNELS_WHATSAPP_INBOUND.value,
        num_partitions=1,
        replication_factor=1,
    ),
    KafkaTopics.CHANNELS_WEBFORM_INBOUND.value: NewTopic(
        name=KafkaTopics.CHANNELS_WEBFORM_INBOUND.value,
        num_partitions=1,
        replication_factor=1,
    ),
    
    # Escalation topic (low volume, important)
    KafkaTopics.ESCALATIONS.value: NewTopic(
        name=KafkaTopics.ESCALATIONS.value,
        num_partitions=1,
        replication_factor=1,
    ),
    
    # Dead Letter Queue
    KafkaTopics.DLQ.value: NewTopic(
        name=KafkaTopics.DLQ.value,
        num_partitions=1,
        replication_factor=1,
    ),
}


async def create_topics(
    bootstrap_servers: str = "localhost:9092",
    topics_to_create: list = None,
) -> None:
    """
    Create Kafka topics.
    
    Args:
        bootstrap_servers: Kafka broker addresses
        topics_to_create: List of topic names to create (default: all)
    """
    admin_client = AIOKafkaAdminClient(bootstrap_servers=bootstrap_servers)
    
    try:
        await admin_client.start()
        logger.info("Connected to Kafka broker", servers=bootstrap_servers)
        
        # Get list of topics to create
        if topics_to_create is None:
            topics_to_create = list(TOPIC_CONFIGS.keys())
        
        # Filter to only topics that don't exist
        existing_topics = await admin_client.list_topics()
        new_topics = [
            TOPIC_CONFIGS[name]
            for name in topics_to_create
            if name not in existing_topics and name in TOPIC_CONFIGS
        ]
        
        if not new_topics:
            logger.info("All topics already exist")
            return
        
        # Create topics
        logger.info("Creating topics", count=len(new_topics))
        
        for topic in new_topics:
            try:
                await admin_client.create_topics([topic])
                logger.info(
                    "Topic created",
                    name=topic.name,
                    partitions=topic.num_partitions,
                    replication=topic.replication_factor
                )
            except Exception as error:
                if "already exists" in str(error).lower():
                    logger.debug("Topic already exists", name=topic.name)
                else:
                    logger.error(
                        "Failed to create topic",
                        name=topic.name,
                        error=str(error)
                    )
        
        logger.info("Topic creation complete")
        
    except Exception as error:
        logger.error("Failed to create topics", error=str(error))
        raise
    finally:
        await admin_client.close()


async def delete_topics(
    bootstrap_servers: str = "localhost:9092",
    topics_to_delete: list = None,
) -> None:
    """
    Delete Kafka topics (for cleanup/testing).
    
    Args:
        bootstrap_servers: Kafka broker addresses
        topics_to_delete: List of topic names to delete
    """
    admin_client = AIOKafkaAdminClient(bootstrap_servers=bootstrap_servers)
    
    try:
        await admin_client.start()
        
        if topics_to_delete is None:
            topics_to_delete = ALL_TOPICS
        
        existing_topics = await admin_client.list_topics()
        to_delete = [name for name in topics_to_delete if name in existing_topics]
        
        if not to_delete:
            logger.info("No topics to delete")
            return
        
        logger.info("Deleting topics", count=len(to_delete))
        
        for topic_name in to_delete:
            try:
                await admin_client.delete_topics([topic_name])
                logger.info("Topic deleted", name=topic_name)
            except Exception as error:
                logger.error("Failed to delete topic", name=topic_name, error=str(error))
        
    except Exception as error:
        logger.error("Failed to delete topics", error=str(error))
        raise
    finally:
        await admin_client.close()


async def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Kafka Topics Management")
    parser.add_argument(
        "--servers",
        default="localhost:9092",
        help="Kafka bootstrap servers"
    )
    parser.add_argument(
        "--delete",
        nargs="+",
        help="Topics to delete (instead of create)"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all existing topics"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger("INFO"),
    )
    
    if args.list:
        admin_client = AIOKafkaAdminClient(bootstrap_servers=args.servers)
        try:
            await admin_client.start()
            topics = await admin_client.list_topics()
            print("\nExisting Kafka Topics:")
            print("-" * 40)
            for topic in sorted(topics):
                print(f"  {topic}")
            print("-" * 40)
            print(f"Total: {len(topics)} topics")
        finally:
            await admin_client.close()
        return
    
    if args.delete:
        await delete_topics(args.servers, args.delete)
    else:
        await create_topics(args.servers)


if __name__ == "__main__":
    asyncio.run(main())
