#!/bin/bash

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   ISL Translator - Deploy with Google Cloud Storage       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

set -e

PROJECT_ID="isl-translator-492416"
BUCKET_NAME="${PROJECT_ID}-videos"
REGION="us-central1"

# Step 1: Create and setup GCS bucket
echo "═══ Step 1: Setting up Google Cloud Storage ═══"
echo ""

if gsutil ls -b gs://${BUCKET_NAME} 2>/dev/null; then
    echo "✓ Bucket already exists: gs://${BUCKET_NAME}"
else
    echo "Creating bucket..."
    gsutil mb -p ${PROJECT_ID} -c STANDARD -l ${REGION} gs://${BUCKET_NAME}
    echo "✓ Created bucket: gs://${BUCKET_NAME}"
fi

echo "Making bucket publicly readable..."
gsutil iam ch allUsers:objectViewer gs://${BUCKET_NAME}
echo "✓ Bucket is public"
echo ""

# Step 2: Upload videos to GCS
echo "═══ Step 2: Uploading videos to GCS ═══"
echo ""

VIDEO_COUNT=$(ls -1 knowledge_base/videos/ | wc -l)
echo "Found $VIDEO_COUNT videos locally"
echo "Uploading to GCS (this may take a few minutes)..."

gsutil -m cp -r knowledge_base/videos/* gs://${BUCKET_NAME}/videos/

UPLOADED_COUNT=$(gsutil ls gs://${BUCKET_NAME}/videos/ | wc -l)
echo "✓ Uploaded $UPLOADED_COUNT videos to GCS"
echo ""

# Step 3: Upload audio files if they exist
echo "═══ Step 3: Uploading audio files ═══"
echo ""

if [ -d "knowledge_base/generated_audio" ] && [ "$(ls -A knowledge_base/generated_audio)" ]; then
    echo "Uploading audio files..."
    gsutil -m cp -r knowledge_base/generated_audio/* gs://${BUCKET_NAME}/audio/ 2>/dev/null || true
    echo "✓ Audio files uploaded"
else
    echo "ℹ No audio files found (this is OK)"
fi
echo ""

# Step 4: Upload metadata
echo "═══ Step 4: Uploading metadata ═══"
echo ""

gsutil cp knowledge_base/metadata.json gs://${BUCKET_NAME}/metadata.json
echo "✓ Metadata uploaded"
echo ""

# Step 5: Test GCS URLs
echo "═══ Step 5: Testing GCS URLs ═══"
echo ""

echo "Testing video URL..."
TEST_VIDEO=$(ls knowledge_base/videos/ | head -1)
TEST_URL="https://storage.googleapis.com/${BUCKET_NAME}/videos/${TEST_VIDEO}"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$TEST_URL")

if [ "$STATUS" = "200" ]; then
    echo "✓ Videos are publicly accessible"
    echo "  Example: $TEST_URL"
else
    echo "⚠ Warning: Got HTTP $STATUS for test video"
fi
echo ""

# Step 6: Deploy to Cloud Run
echo "═══ Step 6: Deploying to Cloud Run ═══"
echo ""
echo "Building and deploying (10-15 minutes)..."
echo ""

gcloud builds submit --config cloudbuild.gcs.yaml .

if [ $? -eq 0 ]; then
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║              ✓ DEPLOYMENT SUCCESSFUL! ✓                   ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    # Wait for service to be ready
    echo "Waiting for service to be ready..."
    sleep 10
    
    # Test deployment
    echo ""
    echo "═══ Testing Deployment ═══"
    APP_URL="https://isl-translator-ggaxczmx5a-uc.a.run.app"
    
    echo -n "Main page: "
    curl -s -o /dev/null -w "HTTP %{http_code}\n" "$APP_URL/"
    
    echo -n "Video endpoint: "
    curl -s -o /dev/null -w "HTTP %{http_code}\n" "$APP_URL/videos/hello.mp4"
    
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║                    SETUP COMPLETE                          ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "🌐 Your app: $APP_URL"
    echo "📦 GCS bucket: gs://${BUCKET_NAME}"
    echo "🎥 Videos: https://storage.googleapis.com/${BUCKET_NAME}/videos/"
    echo ""
    echo "Benefits of this setup:"
    echo "  ✓ Faster deployments (no video uploads)"
    echo "  ✓ Smaller Docker images"
    echo "  ✓ Easy to add/update videos without redeploying"
    echo "  ✓ Better performance"
    echo ""
else
    echo ""
    echo "✗ Deployment failed"
    exit 1
fi
