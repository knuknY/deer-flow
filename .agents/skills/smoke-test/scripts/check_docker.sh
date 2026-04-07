#!/usr/bin/env bash
set -e

echo "=========================================="
echo "  Checking Docker Environment"
echo "=========================================="
echo ""

# Check whether Docker is installed
if command -v docker >/dev/null 2>&1; then
    echo "✓ Docker is installed"
    docker --version
else
    echo "✗ Docker is not installed"
    exit 1
fi
echo ""

# Check the Docker daemon
if docker info >/dev/null 2>&1; then
    echo "✓ Docker daemon is running normally"
else
    echo "✗ Docker daemon is not running"
    echo "  Please start Docker Desktop or the Docker service"
    exit 1
fi
echo ""

# Check Docker Compose
if docker compose version >/dev/null 2>&1; then
    echo "✓ Docker Compose is available"
    docker compose version
else
    echo "✗ Docker Compose is not available"
    exit 1
fi
echo ""

# Check port 2026
if lsof -i :2026 >/dev/null 2>&1; then
    echo "⚠  Port 2026 is already in use"
    echo "  Occupying process:"
    lsof -i :2026
else
    echo "✓ Port 2026 is available"
fi
echo ""

echo "=========================================="
echo "  Docker Environment Check Complete"
echo "=========================================="
