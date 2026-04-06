#!/bin/bash

echo "=== Redeploying ISL Translator with Video Fix ==="
echo ""

echo "1. Verifying videos are present locally..."
VIDEO_COUNT=$(ls -1 knowledge_base/videos/ | wc -l)
echo "   Found $VIDEO_COUNT videos"

if [ "$VIDEO_COUNT" -lt 100 ]; then
    echo "   ⚠️  Warning: Expected ~214 videos, found only $VIDEO_COUNT"
    read -p "   Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "2. Building and deploying with Cloud Build..."
echo "   This will take 10-15 minutes..."
gcloud builds submit --config cloudbuild.yaml .

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Test your app at: https://isl-translator-ggaxczmx5a-uc.a.run.app"
echo ""
echo "To verify videos are working:"
echo "  curl -I https://isl-translator-ggaxczmx5a-uc.a.run.app/videos/hello.mp4"
