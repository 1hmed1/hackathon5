@echo off
REM NovaSaaS Customer Success AI System - Windows Startup Script
REM Usage: start.bat [dev^|prod]

setlocal enabledelayedexpansion

echo.
echo ╔════════════════════════════════════════════════════════╗
echo ║   NovaSaaS Customer Success AI System                  ║
echo ╚════════════════════════════════════════════════════════╝
echo.

REM Check if .env exists
if not exist .env (
    echo ⚠️  .env file not found. Creating from .env.example...
    copy .env.example .env
    echo ⚠️  Please edit .env and add your API keys before starting.
    echo.
)

REM Default mode
set MODE=%1
if "%MODE%"=="" set MODE=dev

if "%MODE%"=="dev" (
    echo 🚀 Starting development stack...
    echo.
    
    REM Start all services
    docker-compose up -d
    
    echo.
    echo ✅ Services started!
    echo.
    echo Service URLs:
    echo   Frontend:  http://localhost:3000
    echo   Backend:   http://localhost:8000
    echo   Backend API: http://localhost:8000/docs
    echo   Agent:     http://localhost:8001
    echo.
    echo Database:
    echo   PostgreSQL: localhost:5432 ^（novasaas/novasaas^)
    echo   Kafka:      localhost:9092
    echo   Redis:      localhost:6379
    echo.
    echo To view logs:
    echo   docker-compose logs -f ^[service^]
    echo.
    echo To stop:
    echo   docker-compose down
    
) else if "%MODE%"=="prod" (
    echo 🚀 Starting production stack...
    echo.
    
    REM Build all services
    docker-compose -f docker-compose.yml build
    
    REM Start all services
    docker-compose up -d
    
    echo.
    echo ✅ Production services started!
    
) else (
    echo ❌ Unknown mode: %MODE%
    echo Usage: start.bat ^[dev^|prod^]
    exit /b 1
)

endlocal
