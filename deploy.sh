#!/bin/bash

# ISL RAG Translator - Cloud Run Deployment Script

set -e

echo ""
echo "🚀 ISL RAG Translator - Cloud Run Deployment"
echo "=============================================="
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed"
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Get project ID
PROJECT_ID=$(gcloud config get-value project 2>/dev/null)
if [ -z "$PROJECT_ID" ]; then
    echo "❌ Error: No GCP project configured"
    echo "Run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "📋 Project ID: $PROJECT_ID"

# Configuration
SERVICE_NAME="isl-translator"
REGION="us-central1"
IMAGE_NAME="gcr.io/$PROJECT_ID/$SERVICE_NAME"

echo ""
echo "⚙️  Configuration:"
echo "   Service Name: $SERVICE_NAME"
echo "   Region: $REGION"
echo "   Image: $IMAGE_NAME"
echo ""

# Enable required APIs
echo "🔧 Enabling required Google Cloud APIs..."
gcloud services enable \
    cloudbuild.googleapis.com \
    run.googleapis.com \
    containerregistry.googleapis.com \
    --project=$PROJECT_ID

echo ""
echo "🏗️  Building Docker image..."
docker build -f Dockerfile.cloudrun -t $IMAGE_NAME:latest .

echo ""
echo "📤 Pushing image to Google Container Registry..."
docker push $IMAGE_NAME:latest

echo ""
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy $SERVICE_NAME \
    --image $IMAGE_NAME:latest \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --memory 4Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --min-instances 0 \
    --port 8080 \
    --project $PROJECT_ID

echo ""
echo "✅ Deployment complete!"
echo ""
echo "🌐 Your application is now live at:"
gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)' --project $PROJECT_ID

echo ""
echo "📊 View logs:"
echo "   gcloud run logs read --service=$SERVICE_NAME --region=$REGION"
echo ""
echo "🔧 Manage service:"
echo "   https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME"
