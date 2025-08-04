#!/bin/bash

# System Optimization Script for 5000+ WebSocket Connections
# Run this before starting the load test for optimal performance

echo "🚀 Optimizing system for 5000+ WebSocket connections..."

# Check current ulimit
echo "Current ulimit -n: $(ulimit -n)"

# Increase file descriptor limits
echo "Setting ulimit -n to 65536..."
ulimit -n 65536

# Verify the change
echo "New ulimit -n: $(ulimit -n)"

# Check Docker resources
echo ""
echo "📊 Docker System Info:"
docker system df

echo ""
echo "💾 Docker Memory Usage:"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"

echo ""
echo "🔧 System Resource Check:"
if command -v nproc &> /dev/null; then
    echo "CPU cores: $(nproc)"
elif command -v sysctl &> /dev/null; then
    echo "CPU cores: $(sysctl -n hw.ncpu)"
else
    echo "CPU cores: Unknown"
fi

if command -v free &> /dev/null; then
    echo "Total memory: $(free -h | grep '^Mem:' | awk '{print $2}')"
    echo "Available memory: $(free -h | grep '^Mem:' | awk '{print $7}')"
elif command -v vm_stat &> /dev/null; then
    echo "Memory info: $(vm_stat | head -4)"
else
    echo "Memory: Unknown"
fi

echo ""
echo "✅ System optimization complete!"
echo ""
echo "🎯 Recommended test command:"
echo "python scripts/load_test.py --connections 5000 --messages 1 --interval 0"