#!/usr/bin/env python3
"""
NovaSaaS Customer Success Agent - CLI Runner

Usage:
    python run_agent.py "My account is locked" --channel email --customer-id 123
    python run_agent.py "How do I reset my password?" --channel whatsapp
    python run_agent.py "This is unacceptable! I want a refund!" --channel chat
"""
import asyncio
import argparse
import asyncpg
import structlog
import sys
from typing import Optional

from customer_success_agent import (
    run_agent,
    set_db_pool,
    create_customer_success_agent,
)

# Configure structured logging
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger("INFO"),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=False,
)

logger = structlog.get_logger()


async def init_db_pool(db_url: Optional[str] = None) -> Optional[asyncpg.Pool]:
    """Initialize database connection pool"""
    if not db_url:
        # Default local development connection
        db_url = "postgresql://postgres:postgres@localhost:5432/novasaas"
    
    try:
        pool = await asyncpg.create_pool(
            db_url,
            min_size=2,
            max_size=5,
            command_timeout=30,
        )
        logger.info("Database pool created successfully", url=db_url)
        return pool
    except Exception as e:
        logger.warning("Failed to connect to database", error=str(e))
        logger.warning("Agent will run without database access - tools will return errors")
        return None


async def main():
    parser = argparse.ArgumentParser(
        description="NovaSaaS Customer Success Agent CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "My account is locked" --channel email --customer-id 123
  %(prog)s "How do I reset my password?" --channel whatsapp
  %(prog)s "This is unacceptable! I want a refund!" --channel chat --escalate
  %(prog)s "Feature request: dark mode" --channel web_form
        """
    )
    
    parser.add_argument(
        "message",
        type=str,
        help="The customer's message to process"
    )
    
    parser.add_argument(
        "--channel", "-c",
        type=str,
        choices=["email", "whatsapp", "web_form", "chat", "phone"],
        default="web_form",
        help="Channel the message came from (default: web_form)"
    )
    
    parser.add_argument(
        "--customer-id", "-i",
        type=int,
        default=1,
        help="Customer ID (default: 1)"
    )
    
    parser.add_argument(
        "--db-url", "-d",
        type=str,
        default=None,
        help="Database connection URL (default: postgresql://postgres:postgres@localhost:5432/novasaas)"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode (continuous conversation)"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        structlog.configure(
            wrapper_class=structlog.make_filtering_bound_logger("DEBUG"),
        )
    
    # Initialize database
    pool = await init_db_pool(args.db_url)
    if pool:
        set_db_pool(pool)
    
    print("\n" + "=" * 60)
    print("🤖 NovaSaaS Customer Success Agent")
    print("=" * 60)
    print(f"Channel: {args.channel}")
    print(f"Customer ID: {args.customer_id}")
    print("-" * 60)
    
    if args.interactive:
        # Interactive mode
        print("\n📝 Interactive mode - type 'quit' or 'exit' to stop\n")
        
        conversation_history = []
        
        while True:
            try:
                user_input = input("👤 Customer: ").strip()
                
                if user_input.lower() in ["quit", "exit", "q"]:
                    print("\n👋 Goodbye!")
                    break
                
                if not user_input:
                    continue
                
                # Build context-aware prompt
                context_message = user_input
                if conversation_history:
                    context_message = f"""Previous conversation:
{chr(10).join(conversation_history[-4:])}

New message: {user_input}"""
                
                print("\n🤖 Agent is thinking...", end="", flush=True)
                response = await run_agent(
                    context_message,
                    channel=args.channel,
                    customer_id=args.customer_id
                )
                print("\r" + " " * 40 + "\r", end="")  # Clear "thinking" line
                
                print(f"🤖 Agent: {response}\n")
                
                # Add to conversation history
                conversation_history.append(f"Customer: {user_input}")
                conversation_history.append(f"Agent: {response}")
                
            except KeyboardInterrupt:
                print("\n\n👋 Goodbye!")
                break
            except Exception as e:
                print(f"\n❌ Error: {e}\n")
    else:
        # Single message mode
        print(f"\n👤 Customer message: \"{args.message}\"\n")
        print("🤖 Agent is processing...\n")
        
        try:
            response = await run_agent(
                args.message,
                channel=args.channel,
                customer_id=args.customer_id
            )
            
            print("-" * 60)
            print("🤖 Agent Response:")
            print("-" * 60)
            print(response)
            print("-" * 60)
            
        except Exception as e:
            print(f"\n❌ Error: {e}\n")
            sys.exit(1)
    
    # Cleanup
    if pool:
        await pool.close()
        logger.info("Database pool closed")


if __name__ == "__main__":
    asyncio.run(main())
