# NovaSaaS Kubernetes Manifests

This directory contains all Kubernetes manifests for deploying the NovaSaaS Customer Success AI System.

## Directory Structure

```
k8s/
├── namespace.yaml              # Namespace definition
├── configmap.yaml              # Non-secret configuration
├── secrets.yaml                # Secret templates (edit before applying!)
├── serviceaccount.yaml         # Service account and RBAC
├── deployment-api.yaml         # FastAPI backend deployment
├── deployment-worker.yaml      # Message processor worker deployment
├── service.yaml                # ClusterIP services
├── ingress.yaml                # NGINX ingress with TLS
├── hpa.yaml                    # Horizontal Pod Autoscalers
└── kafka/                      # Kafka and Zookeeper manifests
    ├── pvc.yaml                # PersistentVolumeClaims
    ├── zookeeper-statefulset.yaml
    └── kafka-statefulset.yaml
```

## Prerequisites

- Kubernetes cluster 1.25+
- kubectl configured
- NGINX Ingress Controller installed
- cert-manager installed (for TLS)
- Metrics Server installed (for HPA)
- StorageClass configured (for PVCs)

## Quick Start

### 1. Configure Secrets

Edit `secrets.yaml` and replace placeholder values:

```bash
# Generate secure passwords
openssl rand -base64 32  # For POSTGRES_PASSWORD
openssl rand -hex 32     # For JWT_SECRET_KEY
```

### 2. Apply Namespace

```bash
kubectl apply -f namespace.yaml
```

### 3. Apply ConfigMap and Secrets

```bash
kubectl apply -f configmap.yaml
kubectl apply -f secrets.yaml
kubectl apply -f serviceaccount.yaml
```

### 4. Apply Kafka Infrastructure

```bash
kubectl apply -f kafka/pvc.yaml
kubectl apply -f kafka/zookeeper-statefulset.yaml
kubectl apply -f kafka/kafka-statefulset.yaml

# Wait for Kafka to be ready
kubectl rollout status statefulset/zookeeper -n customer-success-fte
kubectl rollout status statefulset/kafka -n customer-success-fte
```

### 5. Apply Application Manifests

```bash
kubectl apply -f service.yaml
kubectl apply -f deployment-api.yaml
kubectl apply -f deployment-worker.yaml
kubectl apply -f hpa.yaml
kubectl apply -f ingress.yaml
```

### 6. Verify Deployment

```bash
# Check all pods are running
kubectl get pods -n customer-success-fte

# Check services
kubectl get svc -n customer-success-fte

# Check ingress
kubectl get ingress -n customer-success-fte

# Check HPA
kubectl get hpa -n customer-success-fte

# View logs
kubectl logs -f deployment/backend-api -n customer-success-fte
kubectl logs -f deployment/message-processor -n customer-success-fte
```

## Using Kustomize

For environment-specific configurations:

```bash
# Development
kubectl apply -k k8s/dev/

# Production
kubectl apply -k k8s/prod/
```

## Scaling

### Manual Scaling

```bash
# Scale backend
kubectl scale deployment backend-api --replicas=5 -n customer-success-fte

# Scale workers
kubectl scale deployment message-processor --replicas=10 -n customer-success-fte
```

### Automatic Scaling (HPA)

HPA is configured to scale based on:
- CPU utilization (target: 70%)
- Memory utilization (target: 80%)
- Custom metrics (if available)

```bash
# View HPA status
kubectl get hpa -n customer-success-fte

# View metrics
kubectl top pods -n customer-success-fte
```

## Monitoring

### Prometheus Metrics

All services expose Prometheus metrics on port 9090:

- `/metrics` - Prometheus endpoint
- `/health` - Health check

### Logging

```bash
# Stream all logs
kubectl logs -f -l app.kubernetes.io/name=novasaas -n customer-success-fte

# Stream specific component logs
kubectl logs -f deployment/backend-api -n customer-success-fte
```

## TLS Configuration

The ingress uses cert-manager with Let's Encrypt:

```bash
# Check certificate status
kubectl get certificates -n customer-success-fte

# View certificate details
kubectl describe certificate novasaas-tls-secret -n customer-success-fte
```

## Troubleshooting

### Pod not starting

```bash
# Check pod events
kubectl describe pod <pod-name> -n customer-success-fte

# Check logs
kubectl logs <pod-name> -n customer-success-fte
```

### Kafka issues

```bash
# Check Kafka broker status
kubectl exec -it kafka-0 -n customer-success-fte -- kafka-broker-api-versions --bootstrap-server localhost:9092

# List topics
kubectl exec -it kafka-0 -n customer-success-fte -- kafka-topics --list --bootstrap-server localhost:9092
```

### Database connection issues

```bash
# Test database connection
kubectl exec -it deployment/backend-api -n customer-success-fte -- \
  python -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('postgresql://...'))"
```

## Resource Limits

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit |
|-----------|-------------|-----------|----------------|--------------|
| Backend API | 250m | 500m | 256Mi | 512Mi |
| Worker | 250m | 500m | 256Mi | 512Mi |
| Kafka | 250m | 1000m | 512Mi | 1Gi |
| Zookeeper | 100m | 500m | 256Mi | 512Mi |

## Security

- All secrets are stored in Kubernetes Secrets
- Service accounts with minimal RBAC permissions
- Network policies should be configured separately
- Pod Security Standards: restricted
- TLS enabled for all external traffic

## Backup and Restore

### Backup Secrets

```bash
kubectl get secrets -n customer-success-fte -o yaml > secrets-backup.yaml
```

### Backup ConfigMaps

```bash
kubectl get configmaps -n customer-success-fte -o yaml > configmap-backup.yaml
```

## Cleanup

```bash
# Delete all resources
kubectl delete -f k8s/ --ignore-not-found

# Delete namespace (removes everything)
kubectl delete namespace customer-success-fte
```
