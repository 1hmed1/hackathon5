# NovaSaaS Customer Success AI Agent

AI-powered customer success agent built with the OpenAI Agents SDK.

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

### 1. Set up the database

```bash
# Run the schema to create required tables
psql -U postgres -d novasaas -f ../database/agent_schema.sql
```

### 2. Configure environment

Create a `.env` file:

```bash
OPENAI_API_KEY=sk-your-api-key-here
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/novasaas
```

### 3. Run the agent CLI

```bash
# Single message mode
python run_agent.py "My account is locked" --channel email --customer-id 123

# Interactive mode
python run_agent.py --interactive --channel chat
```

## Available Tools

The agent has access to these function tools:

| Tool | Description |
|------|-------------|
| `search_knowledge_base(query, max_results)` | Search KB articles using text search |
| `create_ticket(customer_id, issue, priority, channel)` | Create a new support ticket |
| `get_customer_history(customer_id)` | Get last 20 messages across all channels |
| `escalate_to_human(ticket_id, reason, urgency)` | Escalate ticket to human support |
| `send_response(ticket_id, message, channel)` | Send channel-formatted response |

## Channel Formatting

The agent adapts responses based on channel:

- **email**: Formal greeting + signature + full detail
- **whatsapp**: Under 300 chars, casual, ends with 📱 tip
- **web_form**: Semi-formal, clean formatting
- **chat**: Conversational, friendly
- **phone**: Professional, empathetic

## System Prompt Rules

The agent follows these core principles:

1. **ALWAYS create a ticket first** before providing substantive help
2. **NEVER discuss pricing** - escalate to human sales team
3. **NEVER promise unconfirmed features** - only discuss documented features
4. **Escalate angry customers** - sentiment < 0.3 triggers escalation
5. **Adapt tone per channel** - match communication style

## Escalation Triggers

- Customer mentions: "cancel", "churn", "competitor", "refund", "lawsuit", "legal"
- Negative sentiment detected
- Pricing/billing disputes
- P1/Critical issues
- Enterprise customers with urgent issues

## Programmatic Usage

```python
import asyncio
from customer_success_agent import run_agent, set_db_pool
import asyncpg

async def main():
    # Set up database connection
    pool = await asyncpg.create_pool("postgresql://...")
    set_db_pool(pool)
    
    # Run the agent
    response = await run_agent(
        message="How do I reset my password?",
        channel="web_form",
        customer_id=123
    )
    print(response)
    
    await pool.close()

asyncio.run(main())
```

## File Structure

```
agent/
├── customer_success_agent.py  # Main agent with function tools
├── run_agent.py               # CLI runner
├── requirements.txt           # Python dependencies
├── core/
│   ├── agent.py              # Legacy agent implementation
│   └── orchestrator.py       # Task orchestration
├── tools/
│   ├── knowledge_tool.py     # Knowledge base search
│   ├── crm_tool.py           # CRM integration
│   ├── email_tool.py         # Email sending
│   └── slack_tool.py         # Slack notifications
└── prompts/
    ├── system.txt            # System prompt
    └── escalation.txt        # Escalation rules
```

## Database Schema

Required tables (created by `agent_schema.sql`):

- `customers` - Customer information
- `tickets` - Support tickets
- `ticket_messages` - Message history
- `knowledge_base` - Help articles (full-text searchable)
- `customer_channel_identifiers` - Multi-channel IDs
- `ticket_sentiments` - Sentiment tracking
- `conversations` - Conversation threads
