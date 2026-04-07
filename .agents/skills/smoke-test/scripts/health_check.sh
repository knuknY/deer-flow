#!/usr/bin/env bash
set +e

echo "=========================================="
echo "  Service Health Check"
echo "=========================================="
echo ""

all_passed=true

# Check container status
echo "1. Checking container status..."
if docker ps --format "{{.Names}}" | grep -q "deer-flow"; then
    echo "✓ Containers are running:"
    docker ps --format "  - {{.Names}} ({{.Status}})"
else
    echo "✗ No DeerFlow-related containers are running"
    all_passed=false
fi
echo ""

# Wait for services to fully start
echo "2. Waiting for services to fully start (30 seconds)..."
sleep 30
echo ""

# Check frontend service
echo "3. Checking frontend service..."
if curl -s -o /dev/null -w "%{http_code}" http://localhost:2026 | grep -q "200\|301\|302"; then
    echo "✓ Frontend service is accessible (http://localhost:2026)"
else
    echo "✗ Frontend service is not accessible"
    all_passed=false
fi
echo ""

# Check API Gateway
echo "4. Checking API Gateway..."
health_response=$(curl -s http://localhost:2026/health 2>/dev/null)
if [ $? -eq 0 ] && [ -n "$health_response" ]; then
    echo "✓ API Gateway health check passed"
    echo "  Response: $health_response"
else
    echo "✗ API Gateway health check failed"
    all_passed=false
fi
echo ""

# Summary
echo "=========================================="
echo "  Health Check Summary"
echo "=========================================="
echo ""
if [ "$all_passed" = true ]; then
    echo "✅ All checks passed!"
    echo ""
    echo "🌐 Application URL: http://localhost:2026"
    exit 0
else
    echo "❌ Some checks failed"
    echo ""
    echo "Please run 'make docker-logs' to view detailed logs"
    exit 1
fi
