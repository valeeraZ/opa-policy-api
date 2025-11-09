.PHONY: help build up down logs restart clean test init-s3

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

build: ## Build Docker images
	docker-compose build

up: ## Start all services
	docker-compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	@make init-s3

down: ## Stop all services
	docker-compose down

logs: ## View logs from all services
	docker-compose logs -f

logs-api: ## View API logs
	docker-compose logs -f api

logs-opa: ## View OPA logs
	docker-compose logs -f opa

logs-db: ## View database logs
	docker-compose logs -f db

restart: ## Restart all services
	docker-compose restart

restart-api: ## Restart API service
	docker-compose restart api

clean: ## Stop services and remove volumes (WARNING: deletes data)
	docker-compose down -v

ps: ## Show service status
	docker-compose ps

shell-api: ## Open shell in API container
	docker-compose exec api bash

shell-db: ## Open PostgreSQL shell
	docker-compose exec db psql -U postgres -d opa_permissions

test: ## Run tests in Docker
	docker-compose exec api pytest

migrate: ## Run database migrations
	docker-compose exec api alembic upgrade head

migrate-create: ## Create new migration (usage: make migrate-create MSG="description")
	docker-compose exec api alembic revision --autogenerate -m "$(MSG)"

init-s3: ## Initialize LocalStack S3 bucket
	@bash scripts/init-localstack.sh || echo "Failed to initialize S3, continuing..."

health: ## Check health of all services
	@echo "API Health:"
	@curl -s http://localhost:8000/health | python -m json.tool || echo "API not responding"
	@echo "\nOPA Health:"
	@curl -s http://localhost:8181/health || echo "OPA not responding"
	@echo "\nDatabase Health:"
	@docker-compose exec db pg_isready -U postgres || echo "Database not responding"

prod-up: ## Start services with production configuration
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

prod-down: ## Stop production services
	docker-compose -f docker-compose.yml -f docker-compose.prod.yml down

rebuild: ## Rebuild and restart API
	docker-compose build api
	docker-compose up -d api

token: ## Generate a test JWT token (admin user)
	@.venv/bin/python scripts/generate_token.py

token-user: ## Generate a test JWT token (regular user)
	@.venv/bin/python scripts/generate_token.py --ad-groups "infodir-app-user" --employee-id E12345 --email user@example.com --name "Regular User"

token-curl: ## Generate curl commands with authentication
	@.venv/bin/python scripts/generate_token.py --output curl
