#!/bin/bash

echo "╔════════════════════════════════════════════════════════════╗"
echo "║   Setup Google Cloud Storage for Videos                   ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

set -e

PROJECT_ID="isl-translator-492416"
BUCKET_NAME="${PROJECT_ID}-videos"
REGION="us-central1"

# Step 1: Create GCS bucket
echo "Step 1: Creating GCS bucket..."
if gsutil ls -b gs://${BUCKET_NAME} 2>/dev/null; then
    echo "✓ Bucket already exists: gs://${BUCKET_NAME}"
else
    gsutil mb -p ${PROJECT_ID} -c STANDARD -l ${REGION} gs://${BUCKET_NAME}
    echo "✓ Created bucket: gs://${BUCKET_NAME}"
fi
echo ""

# Step 2: Make bucket publicly readable
echo "Step 2: Making bucket publicly readable..."
gsutil iam ch allUsers:objectViewer gs://${BUCKET_NAME}
echo "✓ Bucket is now public"
echo ""

# Step 3: Upload videos
echo "Step 3: Uploading videos to GCS..."
echo "   This may take a few minutes..."
gsutil -m cp -r knowledge_base/videos/* gs://${BUCKET_NAME}/videos/

VIDEO_COUNT=$(gsutil ls gs://${BUCKET_NAME}/videos/ | wc -l)
echo "✓ Uploaded $VIDEO_COUNT videos"
echo ""

# Step 4: Upload audio files (if they exist)
if [ -d "knowledge_base/generated_audio" ]; then
    echo "Step 4: Uploading audio files..."
    gsutil -m cp -r knowledge_base/generated_audio/* gs://${BUCKET_NAME}/audio/ 2>/dev/null || echo "  (No audio files found)"
    echo "✓ Audio files uploaded"
fi
echo ""

# Step 5: Upload metadata
echo "Step 5: Uploading metadata..."
gsutil cp knowledge_base/metadata.json gs://${BUCKET_NAME}/metadata.json
echo "✓ Metadata uploaded"
echo ""

echo "╔════════════════════════════════════════════════════════════╗"
echo "║              ✓ GCS Setup Complete! ✓                      ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📦 Bucket: gs://${BUCKET_NAME}"
echo "🌐 Public URL: https://storage.googleapis.com/${BUCKET_NAME}"
echo ""
echo "Example video URL:"
echo "https://storage.googleapis.com/${BUCKET_NAME}/videos/hello.mp4"
echo ""
echo "Next step: Update unified_app.py to use GCS URLs"
