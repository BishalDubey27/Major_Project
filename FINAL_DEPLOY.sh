#!/bin/bash
# FINAL DEPLOYMENT SCRIPT - Complete working solution

set -e

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║   ISL TRANSLATOR - FINAL DEPLOYMENT TO GOOGLE CLOUD RUN       ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

# Step 1: Verify all files are ready
echo "📋 Step 1: Verifying deployment readiness..."
python verify_deployment_ready.py
if [ $? -ne 0 ]; then
    echo "❌ Verification failed! Fix issues before deploying."
    exit 1
fi
echo ""

# Step 2: Check FAISS index exists
echo "🔍 Step 2: Checking FAISS index..."
if [ ! -f "video_index.faiss" ] || [ ! -f "index_map.json" ]; then
    echo "⚠️ FAISS index missing! Generating now..."
    python setup_database.py
    if [ $? -ne 0 ]; then
        echo "❌ FAISS index generation failed!"
        exit 1
    fi
fi
echo "✅ FAISS index ready ($(ls -lh video_index.faiss | awk '{print $5}'))"
echo ""

# Step 3: Deploy to Cloud Run
echo "🚀 Step 3: Deploying to Google Cloud Run..."

PROJECT_ID="isl-translator-492416"
REGION="us-central1"
SERVICE_NAME="isl-translator"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Set project
gcloud config set project ${PROJECT_ID}

# Build the Docker image using Cloud Build
echo "🔨 Building Docker image..."
gcloud builds submit --config cloudbuild.yaml --timeout=20m

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME} \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated \
    --memory 4Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --min-instances 0

echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║   ✅ DEPLOYMENT COMPLETE!                                      ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "🎉 Your ISL Translator is now live!"
echo ""
echo "Test your deployment:"
echo "  1. Visit the URL shown above"
echo "  2. Type 'hello' in the search box"
echo "  3. Video should play correctly"
echo ""
echo "Check health:"
echo "  curl https://your-url.run.app/health"
echo ""
