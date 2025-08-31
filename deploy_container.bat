@echo off
REM Container-based Apify Actor Deployment Script for Windows
REM This script builds a container that handles the entire deployment process internally

setlocal enabledelayedexpansion

echo === Container-based Apify Actor Deployment ===
echo.

REM Check if APIFY_TOKEN is set
if "%APIFY_TOKEN%"=="" (
    echo Error: APIFY_TOKEN environment variable is required
    echo Please set it with: set APIFY_TOKEN=your_token_here
    pause
    exit /b 1
)

REM Check if Docker is available
docker --version >nul 2>&1
if errorlevel 1 (
    echo Error: Docker not found. Please install Docker first.
    pause
    exit /b 1
)

echo Found Docker: 
for /f "tokens=*" %%i in ('docker --version') do echo %%i
echo APIFY_TOKEN is set
echo.

REM Check if we're in the right directory
if not exist "actors" (
    echo Error: actors directory not found
    echo Please run this script from the project root directory
    pause
    exit /b 1
)

if not exist "shared" (
    echo Error: shared directory not found
    echo Please run this script from the project root directory
    pause
    exit /b 1
)

if not exist "Dockerfile.deploy" (
    echo Error: Dockerfile.deploy not found
    pause
    exit /b 1
)

echo Building deployment container...
docker build -f Dockerfile.deploy -t apify-deployer .

if errorlevel 1 (
    echo Failed to build deployment container
    pause
    exit /b 1
)

echo Successfully built deployment container
echo.

echo Running deployment inside container...
docker run --rm -e APIFY_TOKEN="%APIFY_TOKEN%" apify-deployer

echo.
echo Container deployment completed!
pause