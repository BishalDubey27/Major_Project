#!/bin/bash

echo "=== Testing Video Accessibility ==="
echo ""

APP_URL="https://isl-translator-ggaxczmx5a-uc.a.run.app"

# Test a few common video files
TEST_VIDEOS=("hello.mp4" "thank_you.mp4" "good.mp4" "yes.mp4" "no.mp4")

echo "Testing video endpoints..."
for video in "${TEST_VIDEOS[@]}"; do
    echo -n "  $video: "
    STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$APP_URL/videos/$video")
    if [ "$STATUS" = "200" ]; then
        echo "✓ OK"
    else
        echo "✗ Failed (HTTP $STATUS)"
    fi
done

echo ""
echo "Testing main pages..."
echo -n "  Text-to-Sign: "
curl -s -o /dev/null -w "%{http_code}\n" "$APP_URL/"

echo -n "  Sign Recognition: "
curl -s -o /dev/null -w "%{http_code}\n" "$APP_URL/sign_recognition"

echo ""
echo "=== Test Complete ==="
