#!/bin/bash
set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║          NIGHT-FEED DEPLOYMENT SCRIPT                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored messages
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_info() {
    echo -e "${YELLOW}ℹ${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Check if .env exists
if [ ! -f .env ]; then
    print_error ".env file not found!"
    echo "   Please create .env from .env.example and configure API keys"
    echo "   Run: cp .env.example .env && nano .env"
    exit 1
fi

print_success ".env file found"

# Create necessary directories
echo ""
print_info "Creating necessary directories..."
mkdir -p data output/episodes output/scripts
print_success "Directories created"

# Stop running containers
echo ""
print_info "Stopping existing containers..."
docker-compose down || true
print_success "Containers stopped"

# Build all services
echo ""
print_info "Building Docker images (this may take a few minutes)..."
docker-compose build --no-cache
print_success "All services built successfully"

# Start orchestrator and nginx
echo ""
print_info "Starting Night-Feed services..."
docker-compose up -d orchestrator nginx
print_success "Services started"

# Wait for containers to be ready
echo ""
print_info "Waiting for services to initialize..."
sleep 3

# Check service status
echo ""
print_info "Service Status:"
docker-compose ps

# Check if nginx is accessible
echo ""
print_info "Checking NGINX accessibility..."
if docker exec night-feed-nginx ls /usr/share/nginx/html/ > /dev/null 2>&1; then
    print_success "NGINX is running and accessible"
else
    print_error "NGINX might have issues accessing output directory"
fi

# Show recent logs
echo ""
print_info "Recent logs from orchestrator:"
echo "─────────────────────────────────────────────────────────────"
docker-compose logs --tail=20 orchestrator

# Check if feed.xml exists
echo ""
if [ -f output/feed.xml ]; then
    print_success "feed.xml exists at output/feed.xml"

    # Get server IP
    SERVER_IP=$(hostname -I | awk '{print $1}')
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              DEPLOYMENT SUCCESSFUL!                        ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    print_success "Night-Feed is now running!"
    echo ""
    echo "📡 RSS Feed URL:"
    echo "   http://${SERVER_IP}:8080/feed.xml"
    echo ""
    echo "🕐 Next scheduled run:"
    echo "   $(grep DAILY_RUN_TIME .env | cut -d'=' -f2) (Europe/Warsaw)"
    echo ""
else
    print_info "feed.xml not yet generated (will be created on first run)"
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║          DEPLOYMENT SUCCESSFUL - AWAITING FIRST RUN       ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    print_success "Services are running and waiting for scheduled time"
    echo ""
    echo "🕐 Next scheduled run:"
    echo "   $(grep DAILY_RUN_TIME .env | cut -d'=' -f2) (Europe/Warsaw)"
    echo ""
    echo "⚡ To trigger an immediate test run:"
    echo "   docker-compose run collector python /app/collector.py"
    echo "   docker-compose run writer python /app/writer.py"
    echo "   docker-compose run publisher python /app/publisher.py"
    echo ""
fi

# Show useful commands
echo "📋 Useful Commands:"
echo "   View logs:        docker-compose logs -f"
echo "   View status:      docker-compose ps"
echo "   Stop services:    docker-compose down"
echo "   Restart:          docker-compose restart"
echo ""
echo "🔍 Test RSS feed:"
echo "   curl http://localhost:8080/feed.xml"
echo ""

print_success "Deployment complete!"
