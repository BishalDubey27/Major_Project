# Recommended Improvements for ISL Translator

## Priority 1: Critical Fixes (Implement Now) 🔴

### 1. Enhanced Error Handling for Video Serving

**Current Issue:** Basic error handling
**Solution:** Add comprehensive error handling

```python
# In unified_app.py, replace serve_video function:

@app.route('/videos/<path:filename>')
def serve_video(filename):
    """Serve video files with enhanced error handling"""
    # Sanitize filename to prevent directory traversal
    filename = secure_filename(filename)
    video_path = os.path.join('knowledge_base/videos', filename)
    
    # Check if file exists
    if not os.path.exists(video_path):
        logger.error(f"Video not found: {video_path}")
        return jsonify({
            "error": "Video not found",
            "filename": filename,
            "available_videos": len(os.listdir('knowledge_base/videos'))
        }), 404
    
    # Check file size
    file_size = os.path.getsize(video_path)
    logger.info(f"Serving video: {filename} ({file_size} bytes)")
    
    try:
        response = send_from_directory('knowledge_base/videos', filename, 
                                       mimetype='video/mp4')
        # Add caching headers
        response.cache_control.max_age = 86400  # 24 hours
        response.cache_control.public = True
        return response
    except Exception as e:
        logger.error(f"Failed to serve video {filename}: {e}")
        return jsonify({
            "error": "Failed to serve video",
            "details": str(e)
        }), 500
```

### 2. Add Request Logging

```python
# Add at the top of unified_app.py after imports:

from functools import wraps
import time

def log_request(f):
    """Decorator to log request details"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = time.time()
        logger.info(f"Request: {request.method} {request.path} from {request.remote_addr}")
        
        try:
            response = f(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"Response: {response.status_code if hasattr(response, 'status_code') else 'N/A'} - Duration: {duration:.2f}s")
            return response
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"Error in {request.path}: {e} - Duration: {duration:.2f}s")
            raise
    
    return decorated_function

# Apply to critical routes:
@app.route('/search', methods=['POST'])
@log_request
def search():
    # ... existing code
```

### 3. Add Health Check Metrics

```python
# Replace the health_check function:

import psutil
import time

app_start_time = time.time()

@app.route('/health')
def health_check():
    """Enhanced health check with system metrics"""
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        
        # Check if critical components are loaded
        components_status = {
            "text_to_sign": model is not None and metadata_list is not None,
            "sign_to_speech": sign_model_loaded,
            "faiss_index": faiss_index is not None,
            "videos_available": os.path.exists('knowledge_base/videos')
        }
        
        # Count available resources
        video_count = len([f for f in os.listdir('knowledge_base/videos') 
                          if f.endswith('.mp4')]) if os.path.exists('knowledge_base/videos') else 0
        
        return jsonify({
            "status": "healthy" if all(components_status.values()) else "degraded",
            "uptime_seconds": int(time.time() - app_start_time),
            "components": components_status,
            "resources": {
                "total_videos": video_count,
                "metadata_entries": len(metadata_list) if metadata_list else 0,
                "faiss_vectors": faiss_index.ntotal if faiss_index else 0
            },
            "system": {
                "memory_mb": round(memory_info.rss / 1024 / 1024, 2),
                "cpu_percent": psutil.cpu_percent(interval=0.1)
            },
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500
```

---

## Priority 2: Performance Optimizations (Next Week) 🟡

### 1. Video Compression Script

Create `compress_videos.py`:

```python
#!/usr/bin/env python3
"""
Compress videos to reduce size while maintaining quality
Run this before deployment to optimize video files
"""

import os
import subprocess
from pathlib import Path

def compress_video(input_path, output_path, crf=28):
    """
    Compress video using H.264 codec
    CRF: 18-28 (lower = better quality, larger file)
    """
    cmd = [
        'ffmpeg', '-i', input_path,
        '-vcodec', 'h264',
        '-crf', str(crf),
        '-preset', 'medium',
        '-acodec', 'aac',
        '-b:a', '128k',
        '-movflags', '+faststart',  # Enable streaming
        '-y',  # Overwrite output
        output_path
    ]
    
    try:
        subprocess.run(cmd, check=True, capture_output=True)
        
        # Compare sizes
        original_size = os.path.getsize(input_path)
        compressed_size = os.path.getsize(output_path)
        reduction = (1 - compressed_size / original_size) * 100
        
        print(f"✅ {Path(input_path).name}: {original_size/1024/1024:.2f}MB → {compressed_size/1024/1024:.2f}MB ({reduction:.1f}% reduction)")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to compress {input_path}: {e}")
        return False

def main():
    video_dir = Path('knowledge_base/videos')
    output_dir = Path('knowledge_base/videos_compressed')
    output_dir.mkdir(exist_ok=True)
    
    videos = list(video_dir.glob('*.mp4'))
    print(f"Found {len(videos)} videos to compress\n")
    
    total_original = 0
    total_compressed = 0
    
    for video in videos:
        output_path = output_dir / video.name
        
        if compress_video(str(video), str(output_path)):
            total_original += os.path.getsize(video)
            total_compressed += os.path.getsize(output_path)
    
    print(f"\n📊 Total: {total_original/1024/1024:.2f}MB → {total_compressed/1024/1024:.2f}MB")
    print(f"💾 Saved: {(total_original - total_compressed)/1024/1024:.2f}MB ({(1 - total_compressed/total_original)*100:.1f}%)")

if __name__ == '__main__':
    main()
```

### 2. Add Rate Limiting

```python
# Install: pip install Flask-Limiter

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# Apply to search endpoint
@app.route('/search', methods=['POST'])
@limiter.limit("30 per minute")
def search():
    # ... existing code

# Apply to upload endpoint
@app.route('/upload-sign-video', methods=['POST'])
@limiter.limit("10 per minute")
def upload_sign_video():
    # ... existing code
```

### 3. Implement Caching

```python
# Install: pip install Flask-Caching

from flask_caching import Cache

cache = Cache(app, config={
    'CACHE_TYPE': 'simple',
    'CACHE_DEFAULT_TIMEOUT': 300
})

# Cache search results
@app.route('/search', methods=['POST'])
@cache.memoize(timeout=60)  # Cache for 1 minute
def search():
    # ... existing code

# Cache stats
@app.route('/api/stats')
@cache.cached(timeout=300)  # Cache for 5 minutes
def get_stats():
    # ... existing code
```

---

## Priority 3: Feature Enhancements (Future) 🟢

### 1. Search Analytics

```python
# Add to unified_app.py

from collections import defaultdict, deque
from datetime import datetime, timedelta

# Store search analytics
search_analytics = {
    'recent_searches': deque(maxlen=1000),
    'query_counts': defaultdict(int),
    'daily_searches': defaultdict(int)
}

@app.route('/search', methods=['POST'])
def search():
    # ... existing search code
    
    # Track analytics
    search_analytics['recent_searches'].append({
        'query': query,
        'timestamp': datetime.now().isoformat(),
        'results_count': len(playlist),
        'ip': request.remote_addr
    })
    search_analytics['query_counts'][query.lower()] += 1
    today = datetime.now().strftime('%Y-%m-%d')
    search_analytics['daily_searches'][today] += 1
    
    # ... return response

@app.route('/api/analytics')
def get_analytics():
    """Get search analytics"""
    # Get top 10 searches
    top_searches = sorted(
        search_analytics['query_counts'].items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    # Get recent searches (last 24 hours)
    cutoff = datetime.now() - timedelta(hours=24)
    recent = [
        s for s in search_analytics['recent_searches']
        if datetime.fromisoformat(s['timestamp']) > cutoff
    ]
    
    return jsonify({
        'top_searches': [{'query': q, 'count': c} for q, c in top_searches],
        'recent_searches_24h': len(recent),
        'total_searches': sum(search_analytics['query_counts'].values()),
        'daily_breakdown': dict(search_analytics['daily_searches'])
    })
```

### 2. Video Thumbnails

```python
# Create generate_thumbnails.py

import cv2
import os
from pathlib import Path

def generate_thumbnail(video_path, output_path, timestamp=0):
    """Generate thumbnail from video at specific timestamp"""
    cap = cv2.VideoCapture(video_path)
    
    # Seek to timestamp
    cap.set(cv2.CAP_PROP_POS_MSEC, timestamp * 1000)
    
    ret, frame = cap.read()
    if ret:
        # Resize to thumbnail size
        height, width = frame.shape[:2]
        new_width = 320
        new_height = int(height * (new_width / width))
        resized = cv2.resize(frame, (new_width, new_height))
        
        cv2.imwrite(output_path, resized)
        print(f"✅ Generated thumbnail: {output_path}")
    else:
        print(f"❌ Failed to extract frame from {video_path}")
    
    cap.release()

def main():
    video_dir = Path('knowledge_base/videos')
    thumb_dir = Path('knowledge_base/thumbnails')
    thumb_dir.mkdir(exist_ok=True)
    
    for video in video_dir.glob('*.mp4'):
        thumb_path = thumb_dir / f"{video.stem}.jpg"
        if not thumb_path.exists():
            generate_thumbnail(str(video), str(thumb_path))

if __name__ == '__main__':
    main()
```

Add route to serve thumbnails:

```python
@app.route('/thumbnails/<path:filename>')
def serve_thumbnail(filename):
    """Serve video thumbnails"""
    return send_from_directory('knowledge_base/thumbnails', filename)
```

Update templates to use thumbnails:

```html
<!-- In templates/index.html -->
<img src="/thumbnails/{{ video.file | replace('.mp4', '.jpg') }}" 
     alt="{{ video.text }}"
     loading="lazy"
     class="video-thumbnail">
```

### 3. Progressive Web App (PWA)

Create `static/manifest.json`:

```json
{
  "name": "ISL RAG Translator",
  "short_name": "ISL Translator",
  "description": "AI-Powered Indian Sign Language Translation System",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#667eea",
  "theme_color": "#764ba2",
  "orientation": "portrait",
  "icons": [
    {
      "src": "/static/icon-192.png",
      "sizes": "192x192",
      "type": "image/png",
      "purpose": "any maskable"
    },
    {
      "src": "/static/icon-512.png",
      "sizes": "512x512",
      "type": "image/png",
      "purpose": "any maskable"
    }
  ]
}
```

Create `static/sw.js` (Service Worker):

```javascript
const CACHE_NAME = 'isl-translator-v1';
const urlsToCache = [
  '/',
  '/static/manifest.json',
  '/static/icon-192.png',
  '/static/icon-512.png'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(urlsToCache))
  );
});

self.addEventListener('fetch', event => {
  event.respondWith(
    caches.match(event.request)
      .then(response => response || fetch(event.request))
  );
});
```

Add to base template:

```html
<!-- In templates/index.html <head> -->
<link rel="manifest" href="/static/manifest.json">
<meta name="theme-color" content="#764ba2">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">

<script>
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/static/sw.js')
    .then(reg => console.log('Service Worker registered'))
    .catch(err => console.log('Service Worker registration failed'));
}
</script>
```

---

## Testing Improvements

### 1. Unit Tests

Create `tests/test_app.py`:

```python
import unittest
import json
from unified_app import app, get_video_playlist

class TestApp(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True
    
    def test_index_page(self):
        """Test main page loads"""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
    
    def test_search_endpoint(self):
        """Test search functionality"""
        response = self.app.post('/search',
                                data=json.dumps({'query': 'hello'}),
                                content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('playlist', data)
        self.assertGreater(len(data['playlist']), 0)
    
    def test_health_check(self):
        """Test health endpoint"""
        response = self.app.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('status', data)
    
    def test_video_playlist(self):
        """Test video playlist generation"""
        playlist = get_video_playlist('hello world')
        self.assertIsInstance(playlist, list)
        self.assertGreater(len(playlist), 0)
        self.assertIn('file', playlist[0])
        self.assertIn('text', playlist[0])

if __name__ == '__main__':
    unittest.main()
```

Run tests:

```bash
python -m pytest tests/ -v
```

---

## Deployment Best Practices

### 1. Environment Variables

Create `.env.example`:

```bash
# Application
PORT=8080
FLASK_ENV=production
SECRET_KEY=your-secret-key-here

# Google Cloud
PROJECT_ID=isl-translator-492416
REGION=us-central1

# Optional: Cloud Storage
GCS_BUCKET=isl-translator-videos

# Optional: Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Optional: Redis Cache
REDIS_URL=redis://localhost:6379/0
```

### 2. CI/CD Pipeline

Create `.github/workflows/deploy.yml`:

```yaml
name: Deploy to Cloud Run

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Setup Cloud SDK
      uses: google-github-actions/setup-gcloud@v0
      with:
        project_id: ${{ secrets.GCP_PROJECT_ID }}
        service_account_key: ${{ secrets.GCP_SA_KEY }}
    
    - name: Build and Deploy
      run: |
        gcloud builds submit --tag gcr.io/${{ secrets.GCP_PROJECT_ID }}/isl-translator
        gcloud run deploy isl-translator \
          --image gcr.io/${{ secrets.GCP_PROJECT_ID }}/isl-translator \
          --region us-central1 \
          --platform managed \
          --allow-unauthenticated
```

---

## Summary

### Immediate Actions (Today):
1. ✅ Deploy with new Dockerfile
2. ✅ Verify videos load
3. Add enhanced error handling
4. Add request logging
5. Improve health check

### This Week:
1. Compress videos
2. Add rate limiting
3. Implement caching
4. Add search analytics

### Next Month:
1. Generate thumbnails
2. Create PWA
3. Add comprehensive tests
4. Set up CI/CD

### Monitoring:
- Check logs daily
- Monitor error rates
- Track search patterns
- Measure performance metrics

Good luck with your improvements! 🚀
