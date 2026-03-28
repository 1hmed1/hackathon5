@echo off
REM NovaSaaS Kubernetes Deployment Script (Windows)
REM Usage: apply.bat [apply^|delete^|diff]

setlocal enabledelayedexpansion

set NAMESPACE=customer-success-fte
set SCRIPT_DIR=%~dp0

echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║   NovaSaaS Kubernetes Deployment                       ║
echo ╚════════════════════════════════════════════════════════╝
echo.

set ACTION=%1
if "%ACTION%"=="" set ACTION=apply

if "%ACTION%"=="apply" (
    echo Applying Kubernetes manifests...
    echo.
    
    echo Step 1: Creating namespace...
    kubectl apply -f "%SCRIPT_DIR%namespace.yaml"
    
    echo Step 2: Applying ConfigMap and Secrets...
    kubectl apply -f "%SCRIPT_DIR%configmap.yaml"
    kubectl apply -f "%SCRIPT_DIR%secrets.yaml"
    kubectl apply -f "%SCRIPT_DIR%serviceaccount.yaml"
    
    echo Step 3: Applying Kafka infrastructure...
    kubectl apply -f "%SCRIPT_DIR%kafka\pvc.yaml"
    kubectl apply -f "%SCRIPT_DIR%kafka\zookeeper-statefulset.yaml"
    kubectl apply -f "%SCRIPT_DIR%kafka\kafka-statefulset.yaml"
    
    echo Waiting for Zookeeper to be ready...
    kubectl rollout status statefulset/zookeeper -n %NAMESPACE% --timeout=300s
    
    echo Waiting for Kafka to be ready...
    kubectl rollout status statefulset/kafka -n %NAMESPACE% --timeout=300s
    
    echo Step 4: Applying services...
    kubectl apply -f "%SCRIPT_DIR%service.yaml"
    
    echo Step 5: Applying deployments...
    kubectl apply -f "%SCRIPT_DIR%deployment-api.yaml"
    kubectl apply -f "%SCRIPT_DIR%deployment-worker.yaml"
    kubectl apply -f "%SCRIPT_DIR%deployment-frontend.yaml"
    kubectl apply -f "%SCRIPT_DIR%deployment-agent.yaml"
    
    echo Step 6: Applying HorizontalPodAutoscalers...
    kubectl apply -f "%SCRIPT_DIR%hpa.yaml"
    
    echo Step 7: Applying Ingress...
    kubectl apply -f "%SCRIPT_DIR%ingress.yaml"
    
    echo.
    echo Deployment complete!
    echo.
    echo Useful commands:
    echo   kubectl get pods -n %NAMESPACE%
    echo   kubectl get svc -n %NAMESPACE%
    echo   kubectl get ingress -n %NAMESPACE%
    echo   kubectl logs -f deployment/backend-api -n %NAMESPACE%
    
) else if "%ACTION%"=="delete" (
    echo Deleting all NovaSaaS resources...
    echo.
    
    kubectl delete -f "%SCRIPT_DIR%" --ignore-not-found
    
    echo.
    echo Deletion complete!
    
) else if "%ACTION%"=="status" (
    echo NovaSaaS Cluster Status:
    echo.
    
    echo Namespace:
    kubectl get namespace %NAMESPACE%
    echo.
    
    echo Pods:
    kubectl get pods -n %NAMESPACE%
    echo.
    
    echo Services:
    kubectl get svc -n %NAMESPACE%
    echo.
    
    echo Deployments:
    kubectl get deployments -n %NAMESPACE%
    echo.
    
    echo StatefulSets:
    kubectl get statefulsets -n %NAMESPACE%
    echo.
    
    echo HPA:
    kubectl get hpa -n %NAMESPACE%
    echo.
    
    echo Ingress:
    kubectl get ingress -n %NAMESPACE%
    
) else (
    echo Unknown action: %ACTION%
    echo Usage: %0 [apply^|delete^|status]
    exit /b 1
)

endlocal
