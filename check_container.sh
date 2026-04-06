#!/bin/bash

echo "=== Checking Cloud Run Container ==="
echo ""

echo "1. Getting latest revision..."
REVISION=$(gcloud run revisions list --service=isl-translator --region=us-central1 --format="value(name)" --limit=1)
echo "   Latest revision: $REVISION"
echo ""

echo "2. Checking container logs for video-related errors..."
gcloud run services logs read isl-translator --region=us-central1 --limit=100 | grep -i "video\|knowledge_base\|404\|not found" | tail -20
echo ""

echo "3. Checking service details..."
gcloud run services describe isl-translator --region=us-central1 --format="table(status.url,status.conditions[0].type,status.conditions[0].status)"
echo ""

echo "4. Testing if app is responding..."
APP_URL=$(gcloud run services describe isl-translator --region=us-central1 --format="value(status.url)")
echo "   App URL: $APP_URL"
echo -n "   Health check: "
curl -s -o /dev/null -w "%{http_code}\n" "$APP_URL/"
echo ""

echo "=== Check Complete ==="
