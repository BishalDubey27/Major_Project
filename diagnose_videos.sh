#!/bin/bash

echo "=== Diagnosing Video Loading Issue ==="
echo ""

echo "1. Checking local videos..."
echo "   Video count: $(ls -1 knowledge_base/videos/ | wc -l)"
echo "   Total size: $(du -sh knowledge_base/videos/)"
echo ""

echo "2. Testing video endpoint directly..."
curl -I https://isl-translator-ggaxczmx5a-uc.a.run.app/videos/hello.mp4
echo ""

echo "3. Checking Cloud Run logs for errors..."
gcloud run services logs read isl-translator --region=us-central1 --limit=30 | grep -i "video\|error\|404"
echo ""

echo "4. Checking if videos are in Docker image..."
echo "   Building test to verify COPY command..."
docker build -f Dockerfile.cloudrun -t test-image --target builder . 2>&1 | grep -i "knowledge_base"
echo ""

echo "5. Listing what's in .dockerignore..."
echo "   Checking if knowledge_base is excluded:"
grep -i "knowledge" .dockerignore || echo "   ✓ knowledge_base NOT excluded"
echo ""

echo "=== Diagnosis Complete ==="
echo ""
echo "Next steps:"
echo "- If videos aren't in the image, rebuild with: gcloud builds submit --config cloudbuild.yaml ."
echo "- If videos are too large, consider using Google Cloud Storage"
echo "- Check browser console for specific error messages"
