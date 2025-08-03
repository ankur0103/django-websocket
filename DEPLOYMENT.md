# 🚀 Blue-Green Deployment Guide

## Overview
This project uses a blue-green deployment strategy for zero-downtime deployments. Both blue and green environments run simultaneously, but only one serves live traffic at a time.

## Current Status
```bash
# Check current deployment status
make status
```

## Deployment Methods

### Method 1: Deploy to Idle Environment (Recommended)

#### Smart Deploy (Recommended):
```bash
# Automatically detects which environment is idle and deploys to it
make deploy

# Then switch traffic
make promote
```

#### Manual Deploy:

##### When Blue is Active (Green is idle):
```bash
# 1. Deploy new code to Green
make deploy-green

# 2. Test Green environment
curl http://localhost/healthz  # Should still hit Blue
docker logs docker-app_green-1  # Check Green logs

# 3. Switch traffic from Blue → Green
make promote

# 4. Verify switch
make status  # Should show Green as active
```

##### When Green is Active (Blue is idle):
```bash
# 1. Deploy new code to Blue
make deploy-blue

# 2. Test Blue environment
curl http://localhost/healthz  # Should still hit Green
docker logs docker-app_blue-1  # Check Blue logs

# 3. Switch traffic from Green → Blue
make promote

# 4. Verify switch
make status  # Should show Blue as active
```

### Method 2: Full Stack Redeploy
```bash
# Stop everything
make down

# Deploy with new code
make up

# This rebuilds both environments with latest code
```

### Method 3: Rolling Update (Advanced)
```bash
# Deploy to both environments with different versions
docker compose -f docker/compose.yml build app_blue app_green
docker compose -f docker/compose.yml up -d

# Test both environments
make status
```

## Testing New Deployments

### Health Checks
```bash
# Test health endpoint
curl http://localhost/healthz

# Test readiness endpoint  
curl http://localhost/readyz

# Test metrics endpoint
curl http://localhost/metrics
```

### WebSocket Testing
```bash
# Open in browser
http://localhost/test/

# Test WebSocket connection
websocat ws://localhost/ws/chat/
```

### Log Monitoring
```bash
# Monitor active environment logs
docker logs -f docker-app_blue-1    # When Blue is active
docker logs -f docker-app_green-1   # When Green is active

# Monitor nginx logs
docker logs -f docker-nginx-1
```

## Rollback Strategy

### Quick Rollback
```bash
# If new deployment has issues, switch back immediately
make promote  # Switches back to previous environment
```

### Full Rollback
```bash
# Stop everything
make down

# Revert code changes in git
git revert <commit-hash>

# Redeploy with previous version
make up
```

## Environment Variables

### Production Deployment
```bash
# Set production environment variables
export DEBUG=False
export SECRET_KEY=your-production-secret-key
export REDIS_URL=redis://your-redis-host:6379/0
export COLOR=blue  # or green
export WS_BASE_URL=ws://your-domain.com

# Deploy
make up
```

### Local Development
```bash
# Set development environment variables
export DEBUG=True
export SECRET_KEY=dev-secret-key
export REDIS_URL=redis://localhost:6379/0
export COLOR=blue
export WS_BASE_URL=ws://localhost

# Deploy
make up
```

## Monitoring and Observability

### Metrics
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)
- **Application Metrics**: http://localhost/metrics

### Health Checks
- **Liveness**: http://localhost/healthz
- **Readiness**: http://localhost/readyz

### Logs
```bash
# Structured JSON logs
docker logs docker-app_blue-1
docker logs docker-app_green-1
docker logs docker-nginx-1
```

## Troubleshooting

### Common Issues

#### 1. Health Check Failures
```bash
# Check container status
docker ps

# Check health check logs
docker logs docker-app_blue-1 | grep health
docker logs docker-app_green-1 | grep health
```

#### 2. WebSocket Connection Issues
```bash
# Check nginx configuration
docker exec docker-nginx-1 nginx -t

# Check WebSocket routing
curl -I http://localhost/ws/chat/
```

#### 3. Traffic Not Switching
```bash
# Check nginx configuration
cat docker/nginx/nginx.conf | grep app_active

# Reload nginx
docker exec docker-nginx-1 nginx -s reload
```

### Debug Commands
```bash
# Check all container statuses
docker compose -f docker/compose.yml ps

# Check resource usage
docker stats

# Check network connectivity
docker exec docker-app_blue-1 curl http://redis:6379
docker exec docker-app_green-1 curl http://redis:6379
```

## Best Practices

1. **Always test in idle environment first**
2. **Monitor logs during deployment**
3. **Have rollback plan ready**
4. **Use health checks to validate deployments**
5. **Keep both environments identical except for code version**
6. **Use environment variables for configuration**
7. **Monitor metrics before and after deployment**

## Automation

### CI/CD Pipeline Example
```yaml
# Example GitHub Actions workflow
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Deploy to idle environment
        run: |
          docker compose -f docker/compose.yml build app_green
          docker compose -f docker/compose.yml up -d app_green
      
      - name: Run health checks
        run: |
          sleep 30
          curl -f http://localhost/healthz
      
      - name: Promote to active
        run: make promote
      
      - name: Verify deployment
        run: make status
``` 