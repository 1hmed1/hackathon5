-- NovaSaaS Customer Success AI System - Database Schema
-- This file is run on PostgreSQL initialization

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search

-- =============================================================================
-- Customers Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS customers (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE,
    company VARCHAR(255),
    tier VARCHAR(50) DEFAULT 'standard', -- standard, premium, enterprise
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_customers_email ON customers(email);
CREATE INDEX idx_customers_tier ON customers(tier);
CREATE INDEX idx_customers_name_trgm ON customers USING gin(name gin_trgm_ops);

-- =============================================================================
-- Customer Channel Identifiers (for multi-channel support)
-- =============================================================================
CREATE TABLE IF NOT EXISTS customer_channel_identifiers (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER REFERENCES customers(id) ON DELETE CASCADE,
    channel_type VARCHAR(50) NOT NULL, -- email, whatsapp, phone, chat
    channel_id VARCHAR(255) NOT NULL, -- The actual identifier
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
CREATE INDEX idx_tickets_subject_trgm ON tickets USING gin(subject gin_trgm_ops);

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
CREATE INDEX idx_messages_sender_type ON ticket_messages(sender_type);

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
CREATE INDEX idx_conversations_channel ON conversations(channel);

-- =============================================================================
-- Channel Configurations Table (for storing channel settings)
-- =============================================================================
CREATE TABLE IF NOT EXISTS channel_configurations (
    id SERIAL PRIMARY KEY,
    channel_type VARCHAR(50) UNIQUE NOT NULL, -- email, whatsapp, web_form
    config JSONB NOT NULL DEFAULT '{}',
    enabled BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_channel_config_type ON channel_configurations(channel_type);

-- =============================================================================
-- Metrics Snapshots Table (for historical metrics)
-- =============================================================================
CREATE TABLE IF NOT EXISTS metrics_snapshots (
    id SERIAL PRIMARY KEY,
    snapshot_date DATE NOT NULL DEFAULT CURRENT_DATE,
    metric_name VARCHAR(100) NOT NULL,
    metric_value FLOAT NOT NULL,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(snapshot_date, metric_name)
);

CREATE INDEX idx_metrics_date ON metrics_snapshots(snapshot_date);
CREATE INDEX idx_metrics_name ON metrics_snapshots(metric_name);

-- =============================================================================
-- Escalations Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS escalations (
    id SERIAL PRIMARY KEY,
    ticket_id INTEGER REFERENCES tickets(id) ON DELETE CASCADE,
    reason TEXT NOT NULL,
    urgency VARCHAR(50) NOT NULL, -- low, medium, high, critical
    escalated_to VARCHAR(255), -- Role or person
    status VARCHAR(50) DEFAULT 'pending', -- pending, in_progress, resolved
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX idx_escalations_ticket ON escalations(ticket_id);
CREATE INDEX idx_escalations_status ON escalations(status);
CREATE INDEX idx_escalations_created ON escalations(created_at DESC);

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

CREATE TRIGGER update_channel_configurations_updated_at
    BEFORE UPDATE ON channel_configurations
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- Sample Data (for development/testing)
-- =============================================================================

-- Sample customers
INSERT INTO customers (name, email, company, tier) VALUES
    ('John Doe', 'john@example.com', 'Acme Corp', 'enterprise'),
    ('Jane Smith', 'jane@example.com', 'StartupXYZ', 'premium'),
    ('Bob Wilson', 'bob@example.com', 'Small Biz LLC', 'standard')
ON CONFLICT (email) DO NOTHING;

-- Sample channel identifiers
INSERT INTO customer_channel_identifiers (customer_id, channel_type, channel_id)
SELECT c.id, 'email', c.email
FROM customers c
ON CONFLICT (customer_id, channel_type) DO NOTHING;

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

-- Sample channel configurations
INSERT INTO channel_configurations (channel_type, config, enabled) VALUES
    ('email', '{"smtp_host": "smtp.gmail.com", "smtp_port": 587}'::jsonb, true),
    ('whatsapp', '{"twilio_enabled": true}'::jsonb, true),
    ('web_form', '{"enabled": true, "require_auth": false}'::jsonb, true)
ON CONFLICT (channel_type) DO NOTHING;
