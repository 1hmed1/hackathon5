-- NovaSaaS Customer Success AI Agent - Database Schema
-- Run this to set up the required tables for the agent

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- =============================================================================
-- Customers Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    company VARCHAR(255),
    tier VARCHAR(50) DEFAULT 'standard', -- standard, premium, enterprise
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_tier ON customers(tier);

-- =============================================================================
-- Customer Channel Identifiers (for multi-channel support)
-- =============================================================================
CREATE TABLE IF NOT EXISTS customer_channel_identifiers (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
    channel_type VARCHAR(50) NOT NULL, -- email, whatsapp, phone, chat
    channel_id VARCHAR(255) NOT NULL, -- The actual identifier (phone number, chat ID, etc.)
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(customer_id, channel_type)
);

CREATE INDEX idx_customer_channels ON customer_channel_identifiers(customer_id);

-- =============================================================================
-- Tickets Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS tickets (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
    subject VARCHAR(500) NOT NULL,
    description TEXT,
    status VARCHAR(50) DEFAULT 'open', -- open, in_progress, resolved, closed, escalated
    priority VARCHAR(50) DEFAULT 'medium', -- low, medium, high, critical
    channel VARCHAR(50) NOT NULL, -- email, whatsapp, web_form, chat, phone
    category VARCHAR(100),
    assigned_to VARCHAR(255),
    first_response_at TIMESTAMP WITH TIME ZONE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_tickets_customer ON tickets(customer_id);
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_priority ON tickets(priority);
CREATE INDEX idx_tickets_channel ON tickets(channel);
CREATE INDEX idx_tickets_created ON tickets(created_at DESC);

-- =============================================================================
-- Ticket Messages Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS ticket_messages (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER REFERENCES tickets(id) ON DELETE CASCADE,
    sender VARCHAR(255) NOT NULL,
    sender_type VARCHAR(50) NOT NULL, -- customer, agent, system, bot
    message TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_messages_ticket ON ticket_messages(ticket_id);
CREATE INDEX idx_messages_timestamp ON ticket_messages(timestamp DESC);

-- =============================================================================
-- Knowledge Base Table (for search_knowledge_base tool)
-- =============================================================================
CREATE TABLE IF NOT EXISTS knowledge_base (
    id SERIAL PRIMARY KEY,
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    category VARCHAR(100),
    tags TEXT[], -- Array of tags
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Full-text search index
CREATE INDEX idx_knowledge_base_search ON knowledge_base 
    USING GIN(to_tsvector('english', title || ' ' || content));

CREATE INDEX idx_knowledge_base_category ON knowledge_base(category);

-- =============================================================================
-- Ticket Sentiments Table (for tracking sentiment over time)
-- =============================================================================
CREATE TABLE IF NOT EXISTS ticket_sentiments (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER REFERENCES tickets(id) ON DELETE CASCADE,
    sentiment_score FLOAT, -- -1.0 to 1.0
    analyzed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_sentiments_ticket ON ticket_sentiments(ticket_id);

-- =============================================================================
-- Conversations Table (for tracking conversation threads)
-- =============================================================================
CREATE TABLE IF NOT EXISTS conversations (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
    channel VARCHAR(50) NOT NULL,
    status VARCHAR(50) DEFAULT 'active', -- active, closed
    last_message_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    message_count INTEGER DEFAULT 0
);

CREATE INDEX idx_conversations_customer ON conversations(customer_id);
CREATE INDEX idx_conversations_status ON conversations(status);

-- =============================================================================
-- Sample Data (for testing)
-- =============================================================================

-- Sample customers
INSERT INTO customers (name, email, company, tier) VALUES
    ('John Doe', 'john@example.com', 'Acme Corp', 'enterprise'),
    ('Jane Smith', 'jane@example.com', 'StartupXYZ', 'premium'),
    ('Bob Wilson', 'bob@example.com', 'Small Biz LLC', 'standard')
ON CONFLICT (email) DO NOTHING;

-- Sample knowledge base articles
INSERT INTO knowledge_base (title, content, category, tags) VALUES
    (
        'How to Reset Your Password',
        'To reset your password, go to the login page and click "Forgot Password". Enter your email address and we will send you a reset link. The link expires after 24 hours. If you do not receive the email, check your spam folder.',
        'Account',
        ARRAY['password', 'login', 'account', 'security']
    ),
    (
        'Setting Up Two-Factor Authentication',
        'To enable 2FA: 1) Go to Settings > Security, 2) Click "Enable 2FA", 3) Scan the QR code with your authenticator app, 4) Enter the 6-digit code to verify. We recommend using Authy or Google Authenticator.',
        'Security',
        ARRAY['2fa', 'security', 'authentication', 'account']
    ),
    (
        'Understanding Your Dashboard',
        'The NovaSaaS dashboard provides an overview of your key metrics. The top section shows summary statistics. The charts display trends over time. Use the filters to customize the date range and data sources.',
        'Features',
        ARRAY['dashboard', 'analytics', 'metrics', 'ui']
    ),
    (
        'Integration Setup Guide',
        'To set up integrations: 1) Navigate to Settings > Integrations, 2) Choose your desired integration, 3) Follow the authentication steps, 4) Configure sync settings. Supported integrations include Salesforce, Slack, and Zapier.',
        'Integrations',
        ARRAY['integration', 'setup', 'salesforce', 'slack', 'zapier']
    ),
    (
        'Billing and Subscription FAQ',
        'You can view and manage your subscription in Settings > Billing. To upgrade, select a plan and confirm. Downgrades take effect at the next billing cycle. Invoices are sent via email and available in your account.',
        'Billing',
        ARRAY['billing', 'subscription', 'pricing', 'invoice']
    )
ON CONFLICT DO NOTHING;

-- =============================================================================
-- Utility Functions
-- =============================================================================

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Triggers for updated_at
CREATE TRIGGER update_customers_updated_at
    BEFORE UPDATE ON customers
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tickets_updated_at
    BEFORE UPDATE ON tickets
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_knowledge_base_updated_at
    BEFORE UPDATE ON knowledge_base
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
