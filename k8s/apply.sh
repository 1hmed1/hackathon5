#!/bin/bash
# NovaSaaS Kubernetes Deployment Script
# Usage: ./apply.sh [apply|delete|diff]

set -e

NAMESPACE="customer-success-fte"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   NovaSaaS Kubernetes Deployment                       ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
echo ""

ACTION=${1:-apply}

case $ACTION in
  apply)
    echo -e "${GREEN}Applying Kubernetes manifests...${NC}"
    echo ""
    
    # 1. Create namespace
    echo -e "${YELLOW}Step 1: Creating namespace...${NC}"
    kubectl apply -f "$SCRIPT_DIR/namespace.yaml"
    
    # 2. Apply ConfigMap and Secrets
    echo -e "${YELLOW}Step 2: Applying ConfigMap and Secrets...${NC}"
    kubectl apply -f "$SCRIPT_DIR/configmap.yaml"
    kubectl apply -f "$SCRIPT_DIR/secrets.yaml"
    kubectl apply -f "$SCRIPT_DIR/serviceaccount.yaml"
    
    # 3. Apply Kafka infrastructure
    echo -e "${YELLOW}Step 3: Applying Kafka infrastructure...${NC}"
    kubectl apply -f "$SCRIPT_DIR/kafka/pvc.yaml"
    kubectl apply -f "$SCRIPT_DIR/kafka/zookeeper-statefulset.yaml"
    kubectl apply -f "$SCRIPT_DIR/kafka/kafka-statefulset.yaml"
    
    echo -e "${YELLOW}Waiting for Zookeeper to be ready...${NC}"
    kubectl rollout status statefulset/zookeeper -n $NAMESPACE --timeout=300s
    
    echo -e "${YELLOW}Waiting for Kafka to be ready...${NC}"
    kubectl rollout status statefulset/kafka -n $NAMESPACE --timeout=300s
    
    # 4. Apply services
    echo -e "${YELLOW}Step 4: Applying services...${NC}"
    kubectl apply -f "$SCRIPT_DIR/service.yaml"
    
    # 5. Apply deployments
    echo -e "${YELLOW}Step 5: Applying deployments...${NC}"
    kubectl apply -f "$SCRIPT_DIR/deployment-api.yaml"
    kubectl apply -f "$SCRIPT_DIR/deployment-worker.yaml"
    kubectl apply -f "$SCRIPT_DIR/deployment-frontend.yaml"
    kubectl apply -f "$SCRIPT_DIR/deployment-agent.yaml"
    
    # 6. Apply HPA
    echo -e "${YELLOW}Step 6: Applying HorizontalPodAutoscalers...${NC}"
    kubectl apply -f "$SCRIPT_DIR/hpa.yaml"
    
    # 7. Apply Ingress
    echo -e "${YELLOW}Step 7: Applying Ingress...${NC}"
    kubectl apply -f "$SCRIPT_DIR/ingress.yaml"
    
    echo ""
    echo -e "${GREEN}✅ Deployment complete!${NC}"
    echo ""
    echo "Useful commands:"
    echo "  kubectl get pods -n $NAMESPACE"
    echo "  kubectl get svc -n $NAMESPACE"
    echo "  kubectl get ingress -n $NAMESPACE"
    echo "  kubectl logs -f deployment/backend-api -n $NAMESPACE"
    ;;
    
  delete)
    echo -e "${YELLOW}Deleting all NovaSaaS resources...${NC}"
    echo ""
    
    kubectl delete -f "$SCRIPT_DIR/" --ignore-not-found
    
    echo ""
    echo -e "${GREEN}✅ Deletion complete!${NC}"
    ;;
    
  diff)
    echo -e "${YELLOW}Showing diff of what would be applied...${NC}"
    echo ""
    
    kubectl diff -f "$SCRIPT_DIR/" || true
    ;;
    
  status)
    echo -e "${GREEN}NovaSaaS Cluster Status:${NC}"
    echo ""
    
    echo "Namespace:"
    kubectl get namespace $NAMESPACE
    echo ""
    
    echo "Pods:"
    kubectl get pods -n $NAMESPACE
    echo ""
    
    echo "Services:"
    kubectl get svc -n $NAMESPACE
    echo ""
    
    echo "Deployments:"
    kubectl get deployments -n $NAMESPACE
    echo ""
    
    echo "StatefulSets:"
    kubectl get statefulsets -n $NAMESPACE
    echo ""
    
    echo "HPA:"
    kubectl get hpa -n $NAMESPACE
    echo ""
    
    echo "Ingress:"
    kubectl get ingress -n $NAMESPACE
    ;;
    
  *)
    echo -e "${RED}Unknown action: $ACTION${NC}"
    echo "Usage: $0 [apply|delete|diff|status]"
    exit 1
    ;;
esac
