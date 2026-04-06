#!/bin/bash

# ISL Translator - Video Fix & Deployment Script
# Copy this entire file and paste it into Cloud Shell

set -e

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   ISL Translator - Video Fix & Deployment                 ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# Step 1: Verify videos
echo "📋 Step 1: Verifying local videos..."
VIDEO_COUNT=$(ls -1 knowledge_base/videos/ 2>/dev/null | wc -l)
VIDEO_SIZE=$(du -sh knowledge_base/videos/ 2>/dev/null | cut -f1)

echo -e "${GREEN}✓ Videos found${NC}"
echo "  - Count: $VIDEO_COUNT files"
echo "  - Size: $VIDEO_SIZE"
echo ""

# Step 2: Fix Dockerfile
echo "📋 Step 2: Fixing Dockerfile..."

if grep -q "mkdir -p uploads temp_audio knowledge_base/videos" Dockerfile.cloudrun; then
    echo "  Removing knowledge_base/videos from mkdir command..."
    sed -i 's/mkdir -p uploads temp_audio knowledge_base\/videos knowledge_base\/generated_audio/mkdir -p uploads temp_audio knowledge_base\/generated_audio/' Dockerfile.cloudrun
    echo -e "${GREEN}✓ Dockerfile fixed${NC}"
else
    echo -e "${GREEN}✓ Dockerfile already fixed${NC}"
fi
echo ""

# Step 3: Deploy
echo "📋 Step 3: Deploying to Cloud Run..."
echo "This will take 10-15 minutes..."
echo ""

gcloud builds submit --config cloudbuild.yaml .

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✓ Deployment successful!${NC}"
    echo ""
    
    # Test
    echo "📋 Testing deployment..."
    APP_URL="https://isl-translator-ggaxczmx5a-uc.a.run.app"
    
    sleep 5  # Wait for service to be ready
    
    echo -n "  Main page: "
    curl -s -o /dev/null -w "%{http_code}\n" "$APP_URL/"
    
    echo -n "  Video test: "
    curl -s -o /dev/null -w "%{http_code}\n" "$APP_URL/videos/hello.mp4"
    
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              🎉 DEPLOYMENT COMPLETE 🎉                     ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "🌐 Your app: $APP_URL"
    echo ""
else
    echo -e "${RED}✗ Deployment failed${NC}"
    exit 1
fi
