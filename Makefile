# ── Makefile ───────────────────────────────────────────────────────────────
# Convenience commands for Docker operations
# Usage: make <command>

.PHONY: build up down logs shell migrate superuser prod-up prod-down prod-logs ssl

# Development commands
build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f web

shell:
	docker compose exec web python manage.py shell

migrate:
	docker compose exec web python manage.py migrate

migrations:
	docker compose exec web python manage.py makemigrations

superuser:
	docker compose exec web python manage.py createsuperuser

static:
	docker compose exec web python manage.py collectstatic --noinput

# Telegram bot
webhook:
	docker compose exec web python manage.py setwebhook

bot:
	docker compose exec web python manage.py runbot

# Database
backup:
	docker compose exec db pg_dump -U $(DB_USER) $(DB_NAME) > backup_$(shell date +%Y%m%d_%H%M%S).sql

# Production commands
prod-build:
	docker compose -f docker-compose.prod.yml build

prod-up:
	docker compose -f docker-compose.prod.yml up -d

prod-down:
	docker compose -f docker-compose.prod.yml down

prod-logs:
	docker compose -f docker-compose.prod.yml logs -f web

# SSL certificate (run AFTER prod-up)
ssl:
	docker run -it --rm \
		-v $(PWD)/certbot/conf:/etc/letsencrypt \
		-v $(PWD)/certbot/www:/var/www/certbot \
		-p 80:80 \
		certbot/certbot certonly --standalone \
		-d $(DOMAIN) \
		--agree-tos --no-eff-email -m $(EMAIL)

# Clean everything (DANGER - removes all data!)
clean:
	docker compose down -v
	docker system prune -f
