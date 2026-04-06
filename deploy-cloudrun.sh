#!/bin/bash

# ISL Translator - Cloud Run Deployment Script
# This script builds and deploys the application to Google Cloud Run

set -e  # Exit on error

# Configuration
PROJECT_ID="isl-translator-492416"
REGION="us-central1"
SERVICE_NAME="isl-translator"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

echo "========================================="
echo "ISL Translator - Cloud Run Deployment"
echo "========================================="
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed"
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Set project
echo "📍 Setting project to: ${PROJECT_ID}"
gcloud config set project ${PROJECT_ID}

# Build the Docker image using Cloud Build
echo ""
echo "🔨 Building Docker image with Cloud Build..."
gcloud builds submit --tag ${IMAGE_NAME} --dockerfile Dockerfile.cloudrun --timeout=20m

# Deploy to Cloud Run
echo ""
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
echo "========================================="
echo "✅ Deployment Complete!"
echo "========================================="
echo ""
echo "Your application is now live at:"
gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format='value(status.url)'
echo ""
