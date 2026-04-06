#!/bin/bash

echo "=== Debugging Video Deployment Issue ==="
echo ""

# Test 1: Check what HTTP status we get
echo "1. Testing video endpoint..."
curl -I https://isl-translator-ggaxczmx5a-uc.a.run.app/videos/hello.mp4
echo ""

# Test 2: Check logs for file not found errors
echo "2. Checking Cloud Run logs for errors..."
gcloud run services logs read isl-translator --region=us-central1 --limit=50 | grep -i "video\|knowledge_base\|FileNotFoundError\|404\|No such file"
echo ""

# Test 3: Check if we can exec into a container to see files
echo "3. Getting current revision..."
REVISION=$(gcloud run revisions list --service=isl-translator --region=us-central1 --format="value(name)" --limit=1)
echo "   Current revision: $REVISION"
echo ""

# Test 4: Check local files before build
echo "4. Verifying local files..."
echo "   Videos in local directory: $(ls -1 knowledge_base/videos/ | wc -l)"
echo "   Sample videos:"
ls knowledge_base/videos/ | head -5
echo ""

# Test 5: Build locally to test
echo "5. Testing Docker build locally..."
echo "   Building image..."
docker build -f Dockerfile.cloudrun -t test-isl-local . > /dev/null 2>&1

if [ $? -eq 0 ]; then
    echo "   ✓ Build successful"
    echo "   Checking if videos are in the image..."
    docker run --rm test-isl-local ls -la knowledge_base/videos/ | head -10
    echo ""
    echo "   Video count in container:"
    docker run --rm test-isl-local sh -c "ls -1 knowledge_base/videos/ | wc -l"
else
    echo "   ✗ Build failed"
fi

echo ""
echo "=== Debug Complete ==="
