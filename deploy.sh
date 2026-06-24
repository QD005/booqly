#!/bin/bash
# ── deploy.sh ───────────────────────────────────────────────────────────────
# One-command deployment script for Linode server
# Run this ON THE SERVER after uploading your project

set -e  # Exit on any error

echo "🚀 Starting deployment..."

# 1. Create required directories
echo "📁 Creating directories..."
mkdir -p logs certbot/conf certbot/www static media

# 2. Build Docker images
echo "🐳 Building Docker images..."
docker compose -f docker-compose.prod.yml build

# 3. Start services
echo "▶️  Starting services..."
docker compose -f docker-compose.prod.yml up -d

# 4. Wait for database
echo "⏳ Waiting for database..."
sleep 5

# 5. Run migrations
echo "🗄️  Running migrations..."
docker compose -f docker-compose.prod.yml exec -T web python manage.py migrate

# 6. Collect static files
echo "📦 Collecting static files..."
docker compose -f docker-compose.prod.yml exec -T web python manage.py collectstatic --noinput

# 7. Set Telegram webhook
echo "🤖 Setting Telegram webhook..."
docker compose -f docker-compose.prod.yml exec -T web python manage.py setwebhook

echo "✅ Deployment complete!"
echo "🌐 Your app should be running at: https://yourdomain.com"
echo "📊 View logs: docker compose -f docker-compose.prod.yml logs -f web"
