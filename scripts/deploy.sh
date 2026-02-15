#!/bin/bash
set -e

echo "🚀 Deploying Night-Feed to production..."
echo ""

# Variables (EDIT THESE)
SERVER_USER="${SERVER_USER:-ubuntu}"
SERVER_HOST="${SERVER_HOST:-your-server-ip}"
SERVER_DIR="~/night-feed"

# Check if server details are set
if [ "$SERVER_HOST" = "your-server-ip" ]; then
    echo "⚠️  Please edit scripts/deploy.sh and set SERVER_USER and SERVER_HOST"
    echo "   Or set environment variables:"
    echo "   export SERVER_USER=ubuntu"
    echo "   export SERVER_HOST=192.168.1.100"
    exit 1
fi

# Commit and push (if there are changes)
if [[ -n $(git status -s) ]]; then
    echo "📝 Committing local changes..."
    git add .
    read -p "Commit message: " commit_msg
    if [ -z "$commit_msg" ]; then
        commit_msg="Update $(date +%Y-%m-%d)"
    fi
    git commit -m "$commit_msg"
else
    echo "✓ No local changes to commit"
fi

echo ""
echo "⬆️  Pushing to GitHub..."
git push origin main

echo ""
echo "🔧 Deploying to server $SERVER_HOST..."
echo ""

ssh ${SERVER_USER}@${SERVER_HOST} << 'ENDSSH'
    cd ~/night-feed

    echo "📥 Pulling latest changes..."
    git pull origin main

    echo "🔨 Building Docker images..."
    docker-compose build

    echo "🔄 Restarting services..."
    docker-compose up -d orchestrator nginx

    echo ""
    echo "✅ Deployment complete!"
    echo ""
    echo "📊 Service status:"
    docker-compose ps

    echo ""
    echo "📜 Recent logs:"
    docker-compose logs --tail=30

ENDSSH

echo ""
echo "🎉 Deployment successful!"
echo ""
echo "📡 You can check logs with:"
echo "   ssh ${SERVER_USER}@${SERVER_HOST} 'cd ~/night-feed && docker-compose logs -f'"
echo ""
echo "🎙️  RSS feed will be available at:"
echo "   http://${SERVER_HOST}:8080/feed.xml"
