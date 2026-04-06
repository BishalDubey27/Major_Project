#!/bin/bash

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   ISL Translator - Final Video Fix                        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

set -e

# Step 1: Verify videos exist locally
echo "Step 1: Verifying local videos..."
if [ ! -d "knowledge_base/videos" ]; then
    echo "ERROR: knowledge_base/videos directory not found!"
    exit 1
fi

VIDEO_COUNT=$(ls -1 knowledge_base/videos/ | wc -l)
VIDEO_SIZE=$(du -sh knowledge_base/videos/ | cut -f1)

echo "✓ Found $VIDEO_COUNT videos ($VIDEO_SIZE)"
echo ""

# Step 2: Create improved Dockerfile
echo "Step 2: Creating improved Dockerfile..."
cat > Dockerfile.cloudrun << 'DOCKERFILE_END'
# Optimized Dockerfile for Google Cloud Run
FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    ffmpeg \
    wget \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY *.py ./
COPY templates/ ./templates/
COPY static/ ./static/
COPY INCLUDE/ ./INCLUDE/

# EXPLICITLY copy knowledge_base with videos
COPY knowledge_base/ ./knowledge_base/

# Create runtime directories
RUN mkdir -p uploads temp_audio

# Verify videos are in the image
RUN ls -la knowledge_base/videos/ && \
    echo "✓ Videos in container: $(ls -1 knowledge_base/videos/ | wc -l) files"

ENV PORT=8080
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

EXPOSE 8080

CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 unified_app:app
DOCKERFILE_END

echo "✓ Dockerfile updated"
echo ""

# Step 3: Test build locally
echo "Step 3: Testing Docker build locally..."
docker build -f Dockerfile.cloudrun -t test-isl-videos . 2>&1 | tail -20

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Local build successful"
    echo ""
    echo "Verifying videos in test container..."
    CONTAINER_VIDEO_COUNT=$(docker run --rm test-isl-videos sh -c "ls -1 knowledge_base/videos/ 2>/dev/null | wc -l")
    echo "  Videos in container: $CONTAINER_VIDEO_COUNT"
    
    if [ "$CONTAINER_VIDEO_COUNT" -lt 100 ]; then
        echo ""
        echo "⚠️  WARNING: Only $CONTAINER_VIDEO_COUNT videos in container (expected $VIDEO_COUNT)"
        echo "   This means videos are not being copied properly."
        echo ""
        read -p "Continue with deployment anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    else
        echo "  ✓ Videos successfully copied to container!"
    fi
else
    echo "✗ Local build failed"
    exit 1
fi

echo ""

# Step 4: Deploy to Cloud Run
echo "Step 4: Deploying to Cloud Run..."
echo "This will take 10-15 minutes..."
echo ""

gcloud builds submit --config cloudbuild.yaml .

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Deployment successful!"
    echo ""
    
    # Wait for deployment to be ready
    echo "Waiting for service to be ready..."
    sleep 10
    
    # Test the deployment
    echo ""
    echo "Testing deployment..."
    APP_URL="https://isl-translator-ggaxczmx5a-uc.a.run.app"
    
    echo -n "  Main page: "
    MAIN_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$APP_URL/")
    echo "HTTP $MAIN_STATUS"
    
    echo -n "  Video (hello.mp4): "
    VIDEO_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$APP_URL/videos/hello.mp4")
    echo "HTTP $VIDEO_STATUS"
    
    if [ "$VIDEO_STATUS" = "200" ]; then
        echo ""
        echo "╔════════════════════════════════════════════════════════════╗"
        echo "║          ✓ SUCCESS! Videos are working! ✓                 ║"
        echo "╚════════════════════════════════════════════════════════════╝"
    else
        echo ""
        echo "⚠️  Videos still returning HTTP $VIDEO_STATUS"
        echo ""
        echo "Checking logs for errors..."
        gcloud run services logs read isl-translator --region=us-central1 --limit=20 | grep -i "video\|error\|404"
    fi
    
    echo ""
    echo "🌐 Your app: $APP_URL"
    echo ""
else
    echo "✗ Deployment failed"
    exit 1
fi
