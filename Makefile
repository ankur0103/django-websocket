.PHONY: help up down build promote monitor load-test clean logs status deploy-green deploy-blue deploy stop-old test-ws test-ws-smoke test-shutdown test-loki test-observability cleanup-backups

# Default target
help:
	@echo "Django WebSocket Production Service"
	@echo ""
	@echo "Available commands:"
	@echo "  make up          - Start the full stack (blue-green deployment)"
	@echo "  make down        - Stop all services"
	@echo "  make build       - Build all Docker images"
	@echo "  make promote     - Perform blue-green deployment (Docker)"
	@echo "  make promote-local - Perform blue-green deployment (local)"
	@echo "  make deploy-green - Deploy new code to green environment (when blue is active)"
	@echo "  make deploy-blue  - Deploy new code to blue environment (when green is active)"
	@echo "  make deploy      - Smart deploy: automatically deploy to idle environment"
	@echo "  make stop-old    - Stop the old environment after confirming new deployment is stable"
	@echo "  make monitor     - Start monitoring (logs + metrics)"
	@echo "  make load-test   - Run load tests (5000+ concurrent connections)"
	@echo "  make test-ws     - Test WebSocket connectivity (interactive)"
	@echo "  make test-ws-smoke - Test WebSocket connectivity (smoke test)"
	@echo "  make test-shutdown - Test graceful shutdown behavior"
	@echo "  make test-loki     - Test Loki log shipping pipeline"
	@echo "  make test-observability - Run comprehensive observability tests"
	@echo "  make cleanup-backups - Clean up old backup files (keep last 5)"
	@echo "  make logs        - Show logs from all services"
	@echo "  make status      - Show deployment status"
	@echo "  make clean       - Clean up containers and volumes"
	@echo "  make help        - Show this help message"

# Start the full stack
up:
	@echo "Starting Django WebSocket service..."
	docker compose -f docker/compose.yml up -d
	@echo "Services started. Access the application at http://localhost"
	@echo "Metrics: http://localhost/metrics"
	@echo "Grafana: http://localhost:3000 (admin/admin)"
	@echo "Prometheus: http://localhost:9090"

# Stop all services
down:
	@echo "Stopping all services..."
	docker compose -f docker/compose.yml down

# Build all Docker images
build:
	@echo "Building Docker images..."
	docker compose -f docker/compose.yml build

# Perform blue-green deployment
promote:
	@echo "Performing blue-green deployment..."
	./scripts/promote.sh

# Perform local blue-green deployment (without Docker)
promote-local:
	@echo "Performing local blue-green deployment..."
	./scripts/promote-local.sh

# Deploy new code to green environment (when blue is active)
deploy-green:
	@echo "Deploying new code to green environment..."
	@echo "Current status:"
	@./scripts/promote.sh status 2>/dev/null || echo "Status check failed"
	@echo ""
	@echo "Building and starting green environment..."
	docker compose -f docker/compose.yml build app_green
	docker compose -f docker/compose.yml up -d app_green
	@echo ""
	@echo "Green deployment completed!"
	@echo "To switch traffic to green, run: make promote"
	@echo "To check green logs, run: docker logs docker-app_green-1"

# Deploy new code to blue environment (when green is active)
deploy-blue:
	@echo "Deploying new code to blue environment..."
	@echo "Current status:"
	@./scripts/promote.sh status 2>/dev/null || echo "Status check failed"
	@echo ""
	@echo "Building and starting blue environment..."
	docker compose -f docker/compose.yml build app_blue
	docker compose -f docker/compose.yml up -d app_blue
	@echo ""
	@echo "Blue deployment completed!"
	@echo "To switch traffic to blue, run: make promote"
	@echo "To check blue logs, run: docker logs docker-app_blue-1"

# Smart deploy: automatically deploy to idle environment
deploy:
	@echo "Smart deployment: detecting idle environment..."
	@if grep -q "server app_blue:8000" docker/nginx/nginx.conf; then \
		echo "Blue is active, deploying to green..."; \
		$(MAKE) deploy-green; \
	else \
		echo "Green is active, deploying to blue..."; \
		$(MAKE) deploy-blue; \
	fi

# Stop the old environment after confirming new deployment is stable
stop-old:
	@echo "Stopping old environment..."
	@if grep -q "server app_blue:8000" docker/nginx/nginx.conf; then \
		echo "Blue is active, stopping green..."; \
		docker compose -f docker/compose.yml stop app_green; \
	else \
		echo "Green is active, stopping blue..."; \
		docker compose -f docker/compose.yml stop app_blue; \
	fi
	@echo "Old environment stopped successfully!"

# Start monitoring
monitor:
	@echo "Starting monitoring..."
	./scripts/monitor.sh

# Run load tests
load-test:
	@echo "Running load tests..."
	python scripts/load_test.py --target 5000 --duration 120

# Test WebSocket connectivity (interactive mode)
test-ws:
	@echo "Testing WebSocket connectivity (interactive)..."
	python scripts/test_websocket.py --mode interactive

# Test WebSocket connectivity (smoke test)
test-ws-smoke:
	@echo "Testing WebSocket connectivity (smoke test)..."
	python scripts/test_websocket.py --mode smoke

# Test graceful shutdown behavior
test-shutdown:
	@echo "Testing graceful shutdown behavior..."
	python scripts/test_graceful_shutdown.py

# Test Loki log shipping pipeline
test-loki:
	@echo "Testing Loki log shipping pipeline..."
	@./scripts/test_loki.sh

# Run comprehensive observability tests
test-observability:
	@echo "Running comprehensive observability tests..."
	@./scripts/test_observability.sh

# Clean up old backup files
cleanup-backups:
	@echo "Cleaning up old backup files..."
	@echo "Keeping only the 5 most recent backups..."
	@if [ -d "backups" ]; then \
		cd backups && ls -t nginx.conf.* 2>/dev/null | tail -n +6 | xargs -r rm -f && echo "Cleaned backups/"; \
	fi
	@if [ -d "docker/nginx/backups" ]; then \
		cd docker/nginx/backups && ls -t nginx.conf.* 2>/dev/null | tail -n +6 | xargs -r rm -f && echo "Cleaned docker/nginx/backups/"; \
	fi
	@echo "Backup cleanup completed!"

# Show logs
logs:
	docker compose -f docker/compose.yml logs -f

# Show deployment status
status:
	@echo "Deployment status:"
	./scripts/promote.sh status
	@echo ""
	@echo "Service status:"
	docker compose -f docker/compose.yml ps

# Clean up
clean: cleanup-backups
	@echo "Cleaning up containers and volumes..."
	docker compose -f docker/compose.yml down -v
	docker system prune -f
	@echo "Cleanup completed"

# Quick test
test:
	@echo "Running quick connectivity test..."
	@echo "Testing health endpoint..."
	@curl -f http://localhost/healthz || echo "Health check failed"
	@echo "Testing WebSocket endpoint..."
	@curl -f http://localhost/ws/chat/ || echo "WebSocket endpoint failed"
	@echo "Quick test completed"

# Development mode
dev:
	@echo "Starting development mode..."
	cd app && uvicorn app.asgi:application --host 0.0.0.0 --port 8000 --reload

# Install dependencies
install:
	@echo "Installing Python dependencies..."
	pip install -r requirements.txt

# Run Django migrations
migrate:
	@echo "Running Django migrations..."
	cd app && python manage.py migrate

# Create Django superuser
superuser:
	@echo "Creating Django superuser..."
	cd app && python manage.py createsuperuser

# Backup database
backup:
	@echo "Creating database backup..."
	mkdir -p backups
	cp app/db.sqlite3 backups/db_$(date +%Y%m%d_%H%M%S).sqlite3
	@echo "Backup created in backups/"

# Restore database
restore:
	@echo "Restoring database from backup..."
	@if [ -z "$(BACKUP_FILE)" ]; then \
		echo "Usage: make restore BACKUP_FILE=backups/db_YYYYMMDD_HHMMSS.sqlite3"; \
		exit 1; \
	fi
	cp $(BACKUP_FILE) app/db.sqlite3
	@echo "Database restored from $(BACKUP_FILE)" 