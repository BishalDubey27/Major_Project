#!/bin/bash

set -e  # Exit on error

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   ISL Translator - Video Fix & Deployment Script          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Step 1: Verify local setup
echo "📋 Step 1: Verifying local setup..."
echo ""

if [ ! -d "knowledge_base/videos" ]; then
    echo -e "${RED}✗ Error: knowledge_base/videos directory not found!${NC}"
    exit 1
fi

VIDEO_COUNT=$(ls -1 knowledge_base/videos/ | wc -l)
VIDEO_SIZE=$(du -sh knowledge_base/videos/ | cut -f1)

echo -e "${GREEN}✓ Videos directory found${NC}"
echo "  - Video count: $VIDEO_COUNT files"
echo "  - Total size: $VIDEO_SIZE"
echo ""

if [ "$VIDEO_COUNT" -lt 100 ]; then
    echo -e "${YELLOW}⚠️  Warning: Expected ~214 videos, found only $VIDEO_COUNT${NC}"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Step 2: Verify Dockerfile fix
echo "📋 Step 2: Verifying Dockerfile fix..."
echo ""

if grep -q "mkdir -p uploads temp_audio knowledge_base/videos" Dockerfile.cloudrun; then
    echo -e "${RED}✗ Dockerfile still has the bug!${NC}"
    echo "  The line 'mkdir -p ... knowledge_base/videos' will overwrite copied videos."
    echo "  Please remove 'knowledge_base/videos' from that line."
    exit 1
else
    echo -e "${GREEN}✓ Dockerfile fix verified${NC}"
fi
echo ""

# Step 3: Check .dockerignore
echo "📋 Step 3: Checking .dockerignore..."
echo ""

if grep -q "^knowledge_base" .dockerignore; then
    echo -e "${RED}✗ Warning: knowledge_base is excluded in .dockerignore!${NC}"
    echo "  This will prevent videos from being copied to the Docker image."
    read -p "Remove this exclusion? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        sed -i '/^knowledge_base/d' .dockerignore
        echo -e "${GREEN}✓ Removed knowledge_base from .dockerignore${NC}"
    fi
else
    echo -e "${GREEN}✓ knowledge_base is not excluded${NC}"
fi
echo ""

# Step 4: Build and deploy
echo "📋 Step 4: Building and deploying to Cloud Run..."
echo ""
echo "This will take approximately 10-15 minutes."
echo "The build happens on Google's servers, so you can close this terminal if needed."
echo ""

read -p "Start deployment? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Deployment cancelled."
    exit 0
fi

echo ""
echo "🚀 Starting Cloud Build..."
echo ""

gcloud builds submit --config cloudbuild.yaml .

BUILD_STATUS=$?

echo ""
if [ $BUILD_STATUS -eq 0 ]; then
    echo -e "${GREEN}✓ Deployment successful!${NC}"
    echo ""
    
    # Step 5: Test deployment
    echo "📋 Step 5: Testing deployment..."
    echo ""
    
    APP_URL="https://isl-translator-ggaxczmx5a-uc.a.run.app"
    
    echo "Testing main page..."
    MAIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$APP_URL/")
    if [ "$MAIN_STATUS" = "200" ]; then
        echo -e "${GREEN}✓ Main page: OK${NC}"
    else
        echo -e "${RED}✗ Main page: Failed (HTTP $MAIN_STATUS)${NC}"
    fi
    
    echo "Testing video endpoint..."
    VIDEO_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$APP_URL/videos/hello.mp4")
    if [ "$VIDEO_STATUS" = "200" ]; then
        echo -e "${GREEN}✓ Videos: OK${NC}"
    else
        echo -e "${YELLOW}⚠️  Videos: HTTP $VIDEO_STATUS${NC}"
        echo "   If this is 404, videos might not be in the container."
        echo "   Check logs with: gcloud run services logs read isl-translator --region=us-central1"
    fi
    
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                   DEPLOYMENT COMPLETE                      ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "🌐 Your app is live at:"
    echo "   $APP_URL"
    echo ""
    echo "📝 Next steps:"
    echo "   - Open the URL in your browser"
    echo "   - Try the text-to-sign feature"
    echo "   - Check if videos are playing"
    echo ""
    echo "🔍 If videos still don't work:"
    echo "   - Run: ./check_container.sh"
    echo "   - Check browser console for errors"
    echo "   - View logs: gcloud run services logs read isl-translator --region=us-central1"
    echo ""
else
    echo -e "${RED}✗ Deployment failed!${NC}"
    echo ""
    echo "Check the error messages above."
    echo "Common issues:"
    echo "  - Network connectivity"
    echo "  - Insufficient permissions"
    echo "  - Docker build errors"
    echo ""
    exit 1
fi
