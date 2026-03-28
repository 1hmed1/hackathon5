# NovaSaaS Customer Success AI System

A comprehensive AI-powered customer success platform with multi-channel support, automated ticket processing, and intelligent agent responses.

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
![Node](https://img.shields.io/badge/node-20-green.svg)
![Docker](https://img.shields.io/badge/docker-ready-blue.svg)

## 🚀 Quick Start

### Prerequisites

- **Docker & Docker Compose** (v2.0+)
- **Node.js 20+** (optional, for local frontend development)
- **Python 3.11+** (optional, for local backend/agent development)
- **OpenAI API Key** (for AI agent functionality)

### Get Running in 3 Commands

```bash
# 1. Clone and configure
git clone <repository-url> && cd hackathon5
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 2. Start the stack
./start.sh dev    # Linux/Mac
# OR
start.bat dev     # Windows

# 3. Access the application
# Frontend: http://localhost:3000
# Backend API: http://localhost:8000/docs
```

## 📋 Table of Contents

- [Quick Start](#-quick-start)
- [Architecture](#-architecture)
- [Project Structure](#-project-structure)
- [Environment Variables](#-environment-variables)
- [Testing Channels](#-testing-channels)
- [Kubernetes Deployment](#-kubernetes-deployment)
- [Running Tests](#-running-tests)
- [Troubleshooting](#-troubleshooting)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Client Layer                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │
│  │   Web App   │  │  Mobile App │  │  WhatsApp   │  │      Email      │    │
│  │  (Next.js)  │  │   (Future)  │  │   (Twilio)  │  │    (Gmail)      │    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘    │
└─────────┼────────────────┼────────────────┼──────────────────┼─────────────┘
          │                │                │                  │
          ▼                ▼                ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API Gateway                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    NGINX Ingress + TLS (cert-manager)                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Backend Services                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────┐    │
│  │   FastAPI   │  │   AI Agent  │  │   Channel   │  │     Worker      │    │
│  │   Backend   │  │  (OpenAI)   │  │   Handlers  │  │   Processor     │    │
│  │   :8000     │  │   :8001     │  │             │  │                 │    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └────────┬────────┘    │
└─────────┼────────────────┼────────────────┼──────────────────┼─────────────┘
          │                │                │                  │
          ▼                ▼                ▼                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Message Broker                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         Apache Kafka                                 │   │
│  │  Topics: tickets.incoming, channels.*, escalations, metrics, dlq    │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Data Layer                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────────────┐     │
│  │  PostgreSQL │  │    Redis    │  │      Knowledge Base             │     │
│  │  + pgvector │  │   (Cache)   │  │      (Full-text search)         │     │
│  └─────────────┘  └─────────────┘  └─────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 📁 Project Structure

```
hackathon5/
├── backend/                 # FastAPI Backend
│   ├── main.py             # Main application entry
│   ├── channels/           # Channel handlers
│   │   ├── gmail_handler.py
│   │   ├── whatsapp_handler.py
│   │   └── web_form_handler.py
│   ├── kafka_client.py     # Kafka producer/consumer
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/               # Next.js 14 Dashboard
│   ├── app/               # App Router pages
│   │   ├── page.tsx       # Dashboard home
│   │   ├── tickets/       # Tickets pages
│   │   ├── support/       # Support form
│   │   └── ...
│   ├── components/        # React components
│   ├── lib/              # API client
│   └── Dockerfile
│
├── agent/                 # AI Agent (OpenAI Agents SDK)
│   ├── customer_success_agent.py
│   ├── run_agent.py       # CLI runner
│   └── Dockerfile
│
├── workers/               # Kafka Workers
│   ├── message_processor.py
│   └── Dockerfile
│
├── database/              # Database schemas
│   └── schema.sql
│
├── k8s/                   # Kubernetes manifests
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   ├── deployment-*.yaml
│   ├── hpa.yaml
│   ├── ingress.yaml
│   └── kafka/
│       ├── kafka-statefulset.yaml
│       └── zookeeper-statefulset.yaml
│
├── tests/                 # Test suite
│   ├── test_agent.py
│   ├── test_api.py
│   └── conftest.py
│
├── docker-compose.yml     # Local development stack
├── .env.example           # Environment template
└── README.md              # This file
```

## 🔧 Environment Variables

Copy `.env.example` to `.env` and configure:

### Required Variables

```bash
# OpenAI API Key (required for AI agent)
OPENAI_API_KEY=sk-your-key-here

# Database
POSTGRES_PASSWORD=your-secure-password
DATABASE_URL=postgresql://novasaas:password@postgres:5432/novasaas
```

### Optional Variables

```bash
# Twilio (WhatsApp)
TWILIO_ACCOUNT_SID=ACxxxx
TWILIO_AUTH_TOKEN=your-token
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886

# Gmail
GMAIL_SERVICE_ACCOUNT_FILE=/app/credentials/service-account.json
GMAIL_DELEGATED_USER=support@yourdomain.com
GCP_PROJECT_ID=your-project

# Application
LOG_LEVEL=INFO
ENVIRONMENT=development
```

## 🧪 Testing Channels

### 1. Web Form (Always Available)

The web form is the easiest channel to test:

```bash
# Start the stack
./start.sh dev

# Open browser to:
http://localhost:3000/support

# Or submit via API:
curl -X POST http://localhost:8000/api/support/submit \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "subject": "Test Ticket",
    "category": "technical",
    "message": "This is a test message from the API.",
    "priority": "medium"
  }'
```

### 2. WhatsApp Sandbox Setup

To test WhatsApp integration:

1. **Create Twilio Account**: https://www.twilio.com/try-twilio

2. **Enable WhatsApp Sandbox**:
   - Go to Messaging > Try it out > Send a WhatsApp message
   - Follow instructions to join sandbox
   - Note your sandbox number (e.g., `whatsapp:+14155238886`)

3. **Configure Webhook**:
   ```bash
   # For local testing, use ngrok
   ngrok http 8000
   
   # Set webhook URL in Twilio console:
   https://your-ngrok-url.ngrok.io/webhooks/whatsapp
   ```

4. **Update .env**:
   ```bash
   TWILIO_ACCOUNT_SID=ACxxxx
   TWILIO_AUTH_TOKEN=your-token
   TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
   ```

5. **Test**: Send a WhatsApp message to the sandbox number

### 3. Gmail Webhook Setup

To test Gmail integration:

1. **Create Google Cloud Project**: https://console.cloud.google.com

2. **Enable Gmail API**:
   - Go to APIs & Services > Library
   - Search and enable "Gmail API"

3. **Create Service Account**:
   - Go to APIs & Services > Credentials
   - Create Service Account
   - Download JSON key file

4. **Domain-wide Delegation** (for G Suite):
   - In service account, enable "Enable G Suite Domain-wide Delegation"
   - Note the Client ID
   - In Google Admin Console: Security > API Controls > Domain-wide Delegation
   - Add Client ID with scope: `https://www.googleapis.com/auth/gmail.readonly`

5. **Set up Pub/Sub Push**:
   ```bash
   # Create topic
   gcloud pubsub topics create gmail-notifications
   
   # Create subscription with push endpoint
   gcloud pubsub subscriptions create gmail-sub \
     --topic=gmail-notifications \
     --push-endpoint=https://your-ngrok-url.ngrok.io/webhooks/gmail
   ```

6. **Update .env**:
   ```bash
   GMAIL_SERVICE_ACCOUNT_FILE=/path/to/service-account.json
   GMAIL_DELEGATED_USER=your-email@yourdomain.com
   GCP_PROJECT_ID=your-project
   ```

### 4. Using ngrok for Local Webhooks

```bash
# Install ngrok
# Download from https://ngrok.com/

# Start ngrok
ngrok http 8000

# Copy the HTTPS URL and use it for:
# - Twilio webhook
# - Gmail Pub/Sub push endpoint
# - Any other external webhook
```

## ☸️ Kubernetes Deployment

### Prerequisites

- Kubernetes cluster 1.25+
- kubectl configured
- NGINX Ingress Controller
- cert-manager (for TLS)
- Metrics Server (for HPA)

### Deployment Steps

```bash
# 1. Navigate to k8s directory
cd k8s

# 2. Configure secrets (REQUIRED - edit before applying!)
# Edit secrets.yaml with your actual values:
# - OPENAI_API_KEY
# - POSTGRES_PASSWORD
# - GMAIL_CREDENTIALS (base64 encoded JSON)
# - TWILIO_* variables

# 3. Apply all manifests
./apply.sh apply      # Linux/Mac
# OR
apply.bat apply       # Windows

# 4. Verify deployment
kubectl get pods -n customer-success-fte
kubectl get svc -n customer-success-fte
kubectl get ingress -n customer-success-fte

# 5. Check logs
kubectl logs -f deployment/backend-api -n customer-success-fte
kubectl logs -f deployment/message-processor -n customer-success-fte
```

### Scaling

```bash
# Manual scaling
kubectl scale deployment backend-api --replicas=5 -n customer-success-fte

# View HPA status
kubectl get hpa -n customer-success-fte
kubectl top pods -n customer-success-fte
```

### TLS Configuration

The ingress uses cert-manager with Let's Encrypt:

```bash
# Check certificate status
kubectl get certificates -n customer-success-fte

# If using self-signed for testing:
kubectl apply -f - <<EOF
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: selfsigned-issuer
spec:
  selfSigned: {}
EOF
```

## 🧪 Running Tests

### Install Test Dependencies

```bash
cd tests
pip install -r requirements.txt
```

### Run All Tests

```bash
# From project root
pytest tests/ -v

# With coverage
pytest tests/ -v --cov=backend --cov=agent --cov-report=html

# Run specific test file
pytest tests/test_api.py -v

# Run specific test
pytest tests/test_agent.py::test_health_check -v
```

### Test Categories

```bash
# Unit tests only
pytest tests/ -v -m "not integration"

# Integration tests only (requires running services)
pytest tests/ -v -m integration

# Skip slow tests
pytest tests/ -v -m "not slow"
```

### Test Examples

```python
# Test agent behavior
pytest tests/test_agent.py::test_pricing_question_always_escalates -v

# Test API endpoints
pytest tests/test_api.py::test_form_submission_returns_ticket_id -v

# Test with output
pytest tests/test_api.py -v -s --tb=long
```

## 🔍 Troubleshooting

### Common Issues

**Backend won't start:**
```bash
# Check logs
docker-compose logs backend

# Verify database is ready
docker-compose logs postgres

# Restart services
docker-compose restart backend postgres
```

**Kafka connection errors:**
```bash
# Wait for Kafka to be ready (takes ~60 seconds)
docker-compose logs -f kafka

# Check topic creation
docker-compose exec kafka kafka-topics --list --bootstrap-server localhost:9092
```

**Frontend can't connect to backend:**
```bash
# Verify NEXT_PUBLIC_API_URL in .env
# Should be: http://localhost:8000

# Check CORS settings in backend
# Should allow: http://localhost:3000
```

**Agent not responding:**
```bash
# Verify OPENAI_API_KEY is set
echo $OPENAI_API_KEY

# Check agent logs
docker-compose logs agent

# Test agent CLI directly
cd agent
python run_agent.py "Hello" --channel web_form
```

### Reset Everything

```bash
# Stop and remove all containers
docker-compose down -v

# Remove node_modules
rm -rf frontend/node_modules

# Remove Python cache
find . -type d -name "__pycache__" -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Restart
./start.sh dev
```

## 📊 Service URLs

| Service | URL | Description |
|---------|-----|-------------|
| Frontend | http://localhost:3000 | Next.js admin dashboard |
| Backend API | http://localhost:8000 | FastAPI backend |
| API Docs | http://localhost:8000/docs | Swagger/OpenAPI docs |
| Agent | http://localhost:8001 | AI Agent service |
| PostgreSQL | localhost:5432 | Database |
| Kafka | localhost:9092 | Message broker |
| Redis | localhost:6379 | Cache |

## 📝 License

MIT License - See LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Create a Pull Request

## 📞 Support

For support, email support@novasaas.com or create an issue in the repository.
