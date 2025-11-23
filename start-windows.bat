@echo off
REM ============================================
REM OCP Platform - Windows Startup Script
REM ============================================

echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                                                                ║
echo ║     OCP Platform - Windows Startup                            ║
echo ║                                                                ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.

REM Check if Docker is running
echo [1/8] Checking Docker Desktop...
docker info >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker Desktop is not running!
    echo.
    echo Please:
    echo 1. Open Docker Desktop application
    echo 2. Wait for it to fully start ^(green icon in system tray^)
    echo 3. Run this script again
    echo.
    pause
    exit /b 1
)
echo ✓ Docker Desktop is running

REM Check if docker-compose is available
docker-compose version >nul 2>&1
if errorlevel 1 (
    echo ERROR: docker-compose is not available!
    echo Please install Docker Desktop which includes docker-compose
    echo Download from: https://www.docker.com/products/docker-desktop
    pause
    exit /b 1
)
echo ✓ docker-compose is available

REM Create .env file if not exists
echo.
echo [2/8] Setting up environment variables...
if not exist .env (
    echo Creating .env file from .env.example...
    copy .env.example .env >nul
    echo ✓ .env file created
) else (
    echo ✓ .env file already exists
)

REM Create necessary directories
echo.
echo [3/8] Creating directories...
if not exist logs mkdir logs
if not exist ml-models\nlu mkdir ml-models\nlu
if not exist ml-models\stt mkdir ml-models\stt
if not exist ml-models\tts mkdir ml-models\tts
if not exist audio-storage mkdir audio-storage
if not exist tmp mkdir tmp
echo ✓ Directories created

REM Stop any existing containers
echo.
echo [4/8] Stopping existing containers...
docker-compose down >nul 2>&1
echo ✓ Old containers stopped

REM Start infrastructure services first
echo.
echo [5/8] Starting infrastructure ^(PostgreSQL ^& Redis^)...
docker-compose up -d postgres redis adminer
echo Waiting for PostgreSQL to be ready...

REM Wait for PostgreSQL
:wait_postgres
timeout /t 2 /nobreak >nul
docker-compose exec -T postgres pg_isready -U ocpuser -d ocplatform >nul 2>&1
if errorlevel 1 (
    echo .
    goto wait_postgres
)

echo.
echo ✓ PostgreSQL is ready
echo ✓ Redis is ready

REM Build all services
echo.
echo [6/8] Building application services...
echo This may take 2-3 minutes on first run...
docker-compose build orchestrator nlu-service chat-connector chat-widget
if errorlevel 1 (
    echo ERROR: Build failed! Check the output above for errors.
    pause
    exit /b 1
)
echo ✓ Services built successfully

REM Start all application services
echo.
echo [7/8] Starting application services...
docker-compose up -d

echo Waiting for services to start...
timeout /t 5 /nobreak >nul

REM Wait for NLU model training
echo.
echo [8/8] Waiting for NLU model training...
echo This may take 30-60 seconds on first startup...
timeout /t 10 /nobreak >nul

REM Display status
echo.
echo Checking service status...
docker-compose ps

REM Display success message
echo.
echo ╔════════════════════════════════════════════════════════════════╗
echo ║                    ALL SERVICES RUNNING!                       ║
echo ╚════════════════════════════════════════════════════════════════╝
echo.
echo 🌐 Access Points:
echo   • Chat Widget:    http://localhost:3000  ← Start here!
echo   • API Docs:       http://localhost:8000/docs
echo   • NLU Docs:       http://localhost:8001/docs
echo   • Database UI:    http://localhost:8080
echo.
echo 🔧 Useful Commands:
echo   • View logs:      docker-compose logs -f
echo   • Stop services:  docker-compose down
echo   • Restart:        docker-compose restart
echo.
echo 🚀 Platform is ready! Open http://localhost:3000 and start chatting!
echo.
pause
