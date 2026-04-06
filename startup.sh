#!/bin/bash
# Startup script for Cloud Run deployment

set -e

echo "========================================="
echo "ISL Translator - Starting Up"
echo "========================================="

# Check critical files
echo "🔍 Checking critical files..."

if [ ! -f "knowledge_base/metadata.json" ]; then
    echo "❌ ERROR: metadata.json not found!"
    echo "Generating metadata from video files..."
    python generate_metadata.py || exit 1
fi

if [ ! -d "knowledge_base/videos" ]; then
    echo "❌ ERROR: videos directory not found!"
    exit 1
fi

VIDEO_COUNT=$(ls -1 knowledge_base/videos/*.mp4 2>/dev/null | wc -l)
echo "✅ Found $VIDEO_COUNT video files"

# Create required directories
echo "📁 Creating required directories..."
mkdir -p uploads temp_audio knowledge_base/generated_audio

# Check FAISS index (CRITICAL for /search endpoint)
if [ ! -f "video_index.faiss" ] || [ ! -f "index_map.json" ]; then
    echo "⚠️ FAISS index missing! Regenerating..."
    python setup_database.py || (echo "❌ FAISS index generation failed!" && exit 1)
fi

echo "✅ FAISS index verified"

# Generate audio files if missing (optional, can be done at runtime)
AUDIO_COUNT=$(ls -1 knowledge_base/generated_audio/*.mp3 2>/dev/null | wc -l)
echo "🎵 Found $AUDIO_COUNT audio files"

if [ "$AUDIO_COUNT" -lt "$VIDEO_COUNT" ]; then
    echo "⚠️ Some audio files missing. They will be generated on-demand."
fi

echo "========================================="
echo "✅ Startup checks complete!"
echo "========================================="

# Start the application
exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 unified_app:app
