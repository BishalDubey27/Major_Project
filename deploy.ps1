# ISL RAG Translator - Cloud Run Deployment Script (PowerShell)

$ErrorActionPreference = "Stop"

Write-Host "`n🚀 ISL RAG Translator - Cloud Run Deployment" -ForegroundColor Cyan
Write-Host "==============================================" -ForegroundColor Cyan
Write-Host ""

# Check if gcloud is installed
try {
    $null = Get-Command gcloud -ErrorAction Stop
} catch {
    Write-Host "❌ Error: gcloud CLI is not installed" -ForegroundColor Red
    Write-Host "Please install it from: https://cloud.google.com/sdk/docs/install" -ForegroundColor Yellow
    exit 1
}

# Get project ID
$PROJECT_ID = (gcloud config get-value project 2>$null)
if ([string]::IsNullOrEmpty($PROJECT_ID)) {
    Write-Host "❌ Error: No GCP project configured" -ForegroundColor Red
    Write-Host "Run: gcloud config set project YOUR_PROJECT_ID" -ForegroundColor Yellow
    exit 1
}

Write-Host "📋 Project ID: $PROJECT_ID" -ForegroundColor Green

# Configuration
$SERVICE_NAME = "isl-translator"
$REGION = "us-central1"
$IMAGE_NAME = "gcr.io/$PROJECT_ID/$SERVICE_NAME"

Write-Host ""
Write-Host "⚙️  Configuration:" -ForegroundColor Cyan
Write-Host "   Service Name: $SERVICE_NAME"
Write-Host "   Region: $REGION"
Write-Host "   Image: $IMAGE_NAME"
Write-Host ""

# Enable required APIs
Write-Host "🔧 Enabling required Google Cloud APIs..." -ForegroundColor Yellow
gcloud services enable `
    cloudbuild.googleapis.com `
    run.googleapis.com `
    containerregistry.googleapis.com `
    --project=$PROJECT_ID

Write-Host ""
Write-Host "🏗️  Building Docker image..." -ForegroundColor Yellow
docker build -f Dockerfile.cloudrun -t "${IMAGE_NAME}:latest" .

Write-Host ""
Write-Host "📤 Pushing image to Google Container Registry..." -ForegroundColor Yellow
docker push "${IMAGE_NAME}:latest"

Write-Host ""
Write-Host "🚀 Deploying to Cloud Run..." -ForegroundColor Yellow
gcloud run deploy $SERVICE_NAME `
    --image "${IMAGE_NAME}:latest" `
    --platform managed `
    --region $REGION `
    --allow-unauthenticated `
    --memory 4Gi `
    --cpu 2 `
    --timeout 300 `
    --max-instances 10 `
    --min-instances 0 `
    --port 8080 `
    --project $PROJECT_ID

Write-Host ""
Write-Host "✅ Deployment complete!" -ForegroundColor Green
Write-Host ""
Write-Host "🌐 Your application is now live at:" -ForegroundColor Cyan
$SERVICE_URL = gcloud run services describe $SERVICE_NAME --region $REGION --format 'value(status.url)' --project $PROJECT_ID
Write-Host $SERVICE_URL -ForegroundColor Green

Write-Host ""
Write-Host "📊 View logs:" -ForegroundColor Cyan
Write-Host "   gcloud run logs read --service=$SERVICE_NAME --region=$REGION" -ForegroundColor Yellow
Write-Host ""
Write-Host "🔧 Manage service:" -ForegroundColor Cyan
Write-Host "   https://console.cloud.google.com/run/detail/$REGION/$SERVICE_NAME" -ForegroundColor Yellow
