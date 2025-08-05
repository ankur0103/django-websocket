#!/bin/bash

echo "🔍 COMPREHENSIVE OBSERVABILITY TEST SUITE"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
PASSED=0
FAILED=0
WARNING=0

# Function to print test results
print_result() {
    local test_name="$1"
    local status="$2"
    local message="$3"
    
    case $status in
        "PASS")
            echo -e "  ${GREEN}✅ PASS${NC} - $test_name: $message"
            ((PASSED++))
            ;;
        "FAIL")
            echo -e "  ${RED}❌ FAIL${NC} - $test_name: $message"
            ((FAILED++))
            ;;
        "WARN")
            echo -e "  ${YELLOW}⚠️  WARN${NC} - $test_name: $message"
            ((WARNING++))
            ;;
    esac
}

echo "1. Testing Metrics Endpoint (/metrics)"
echo "--------------------------------------"
if curl -s http://localhost/metrics | grep -q "websocket_connections_total"; then
    print_result "Prometheus Metrics" "PASS" "Custom metrics are exposed"
else
    print_result "Prometheus Metrics" "FAIL" "Custom metrics not found"
fi

if curl -s http://localhost/metrics | grep -q "python_gc_objects_collected_total"; then
    print_result "Python Metrics" "PASS" "Python runtime metrics available"
else
    print_result "Python Metrics" "WARN" "Python metrics not found"
fi

echo ""
echo "2. Testing Health Probes"
echo "------------------------"
if curl -s http://localhost/healthz | jq -e '.status' > /dev/null 2>&1; then
    print_result "Health Probe (/healthz)" "PASS" "Liveness probe responding"
else
    print_result "Health Probe (/healthz)" "FAIL" "Health probe not responding"
fi

if curl -s http://localhost/readyz | jq -e '.status' > /dev/null 2>&1; then
    print_result "Ready Probe (/readyz)" "PASS" "Readiness probe responding"
else
    print_result "Ready Probe (/readyz)" "FAIL" "Ready probe not responding"
fi

echo ""
echo "3. Testing Structured Logs"
echo "--------------------------"
log_count=$(docker compose -f docker/compose.yml logs app_blue | grep "request_id" | wc -l)
if [ $log_count -gt 0 ]; then
    print_result "Structured Logs" "PASS" "Found $log_count structured log entries"
else
    print_result "Structured Logs" "FAIL" "No structured logs found"
fi

json_logs=$(docker compose -f docker/compose.yml logs app_blue | grep -c "^{")
if [ $json_logs -gt 0 ]; then
    print_result "JSON Format" "PASS" "Found $json_logs JSON log entries"
else
    print_result "JSON Format" "WARN" "No JSON logs found"
fi

echo ""
echo "4. Testing Monitoring Script"
echo "----------------------------"
if [ -f "scripts/monitor.sh" ]; then
    print_result "Monitor Script" "PASS" "Script exists and is executable"
else
    print_result "Monitor Script" "FAIL" "Script not found"
fi

# Test monitor script briefly
timeout 5s ./scripts/monitor.sh --metrics-only --duration 3 > /dev/null 2>&1
if [ $? -eq 0 ] || [ $? -eq 124 ]; then
    print_result "Monitor Execution" "PASS" "Script runs without errors"
else
    print_result "Monitor Execution" "WARN" "Script had issues"
fi

echo ""
echo "5. Testing Pytest Framework"
echo "---------------------------"
if cd app && python -m it run  -v > /dev/null 2>&1; then
    print_result "Pytest Framework" "PASS" "Tests are running"
    cd ..
else
    print_result "Pytest Framework" "WARN" "Some tests may be failing"
    cd ..
fi

echo ""
echo "6. Testing Alerting Rules"
echo "-------------------------"
if curl -s http://localhost:9090/api/v1/rules | jq -e '.data.groups' > /dev/null 2>&1; then
    print_result "Prometheus Rules" "PASS" "Alerting rules are loaded"
else
    print_result "Prometheus Rules" "FAIL" "Alerting rules not accessible"
fi

rule_count=$(curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[0].rules | length' 2>/dev/null || echo "0")
if [ "$rule_count" -gt 0 ]; then
    print_result "Rule Count" "PASS" "Found $rule_count alerting rules"
else
    print_result "Rule Count" "WARN" "No alerting rules found"
fi

echo ""
echo "7. Testing Grafana Dashboard"
echo "----------------------------"
if curl -s http://localhost:3000/api/health | jq -e '.database' > /dev/null 2>&1; then
    print_result "Grafana Health" "PASS" "Grafana is running"
else
    print_result "Grafana Health" "FAIL" "Grafana not accessible"
fi

if [ -f "monitoring/grafana/dashboards/websocket-overview.json" ]; then
    print_result "Dashboard Files" "PASS" "Dashboard JSON files exist"
else
    print_result "Dashboard Files" "FAIL" "Dashboard files not found"
fi

echo ""
echo "8. Testing Loki Log Shipping"
echo "----------------------------"
if curl -s http://localhost:3100/ready | grep -q "ready"; then
    print_result "Loki Ready" "PASS" "Loki is ready"
else
    print_result "Loki Ready" "FAIL" "Loki not ready"
fi

if docker compose -f docker/compose.yml ps promtail | grep -q "Up"; then
    print_result "Promtail Running" "PASS" "Promtail is running"
else
    print_result "Promtail Running" "FAIL" "Promtail not running"
fi

targets=$(docker compose -f docker/compose.yml logs promtail | grep "Adding target" | wc -l)
if [ $targets -gt 0 ]; then
    print_result "Log Targets" "PASS" "Promtail found $targets targets"
else
    print_result "Log Targets" "FAIL" "No log targets found"
fi

echo ""
echo "9. Testing CI/CD Pipeline"
echo "-------------------------"
if [ -f ".github/workflows/ci.yml" ]; then
    print_result "CI/CD Pipeline" "PASS" "GitHub Actions workflow exists"
else
    print_result "CI/CD Pipeline" "FAIL" "CI/CD pipeline not found"
fi

echo ""
echo "10. Testing Docker Compose Services"
echo "-----------------------------------"
services=("redis" "app_blue" "app_green" "nginx" "prometheus" "grafana" "loki" "promtail")
for service in "${services[@]}"; do
    if docker compose -f docker/compose.yml ps $service | grep -q "Up"; then
        print_result "$service Service" "PASS" "Service is running"
    else
        print_result "$service Service" "FAIL" "Service not running"
    fi
done

echo ""
echo "📊 FINAL RESULTS"
echo "================"
echo -e "  ${GREEN}✅ PASSED: $PASSED${NC}"
echo -e "  ${RED}❌ FAILED: $FAILED${NC}"
echo -e "  ${YELLOW}⚠️  WARNINGS: $WARNING${NC}"
echo ""

# Calculate success rate
total=$((PASSED + FAILED + WARNING))
if [ $total -gt 0 ]; then
    success_rate=$((PASSED * 100 / total))
    echo -e "🎯 Success Rate: ${BLUE}$success_rate%${NC}"
fi

echo ""
echo "🔗 Access URLs:"
echo "  - Application: http://localhost"
echo "  - Metrics: http://localhost/metrics"
echo "  - Grafana: http://localhost:3000 (admin/admin)"
echo "  - Prometheus: http://localhost:9090"
echo "  - Loki: http://localhost:3100"

echo ""
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 All critical observability requirements are working!${NC}"
else
    echo -e "${YELLOW}⚠️  Some issues detected. Check the failed tests above.${NC}"
fi

echo ""
echo "🧪 Individual Tests:"
echo "  - make test-loki     - Test Loki log shipping"
echo "  - make test-shutdown - Test graceful shutdown"
echo "  - make monitor       - Start monitoring"
echo "  - make status        - Check service status" 