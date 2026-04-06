# Quick Deployment Guide - ISL Translator

## 🚀 Deploy to Cloud Run (Fix Video Loading Issue)

### Prerequisites
- Google Cloud SDK installed
- Logged in: `gcloud auth login`
- Project set: `gcloud config set project isl-translator-492416`

### Option 1: Automated Deployment (Recommended)

```bash
# Make script executable
chmod +x deploy-cloudrun.sh

# Run deployment
./deploy-cloudrun.sh
```

### Option 2: Manual Deployment

```bash
# Build image with Cloud Build
gcloud builds submit --tag gcr.io/isl-translator-492416/isl-translator --timeout=20m

# Deploy to Cloud Run
gcloud run deploy isl-translator \
    --image gcr.io/isl-translator-492416/isl-translator \
    --platform managed \
    --region us-central1 \
    --allow-unauthenticated \
    --memory 4Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10
```

### Verify Deployment

After deployment, test these URLs:

1. **Main App**: https://isl-translator-ggaxczmx5a-uc.a.run.app/
2. **Test Video**: https://isl-translator-ggaxczmx5a-uc.a.run.app/videos/hello.mp4
3. **Health Check**: https://isl-translator-ggaxczmx5a-uc.a.run.app/health
4. **Stats**: https://isl-translator-ggaxczmx5a-uc.a.run.app/api/stats

### View Logs

```bash
# Real-time logs
gcloud run logs tail isl-translator --region us-central1

# Recent logs
gcloud run logs read isl-translator --region us-central1 --limit 50
```

### Troubleshooting

#### Videos Still Not Loading?

1. Check if videos are in the image:
```bash
# Get service details
gcloud run services describe isl-translator --region us-central1

# Check logs for file not found errors
gcloud run logs read isl-translator --region us-central1 | grep "Video not found"
```

2. Verify video files locally:
```bash
ls -lh knowledge_base/videos/ | head -10
```

3. Test video endpoint directly:
```bash
curl -I https://isl-translator-ggaxczmx5a-uc.a.run.app/videos/hello.mp4
```

#### Build Fails?

- Check Dockerfile syntax
- Ensure all dependencies in requirements.txt
- Increase timeout: `--timeout=30m`

#### Out of Memory?

- Increase memory: `--memory 8Gi`
- Reduce model size or use CPU-only versions

---

## 📝 What Was Fixed

### Issue: Videos Not Loading on Cloud Run

**Root Cause:**
- No Dockerfile configured
- Videos not included in container
- App not using Cloud Run's PORT variable

**Solution:**
1. ✅ Created `Dockerfile.cloudrun` - Properly containerizes app with all dependencies
2. ✅ Created `.dockerignore` - Optimizes build by excluding unnecessary files
3. ✅ Updated `unified_app.py` - Now reads PORT from environment
4. ✅ Created deployment script - Automates the deployment process

### Files Created/Modified:
- `Dockerfile.cloudrun` (new)
- `.dockerignore` (new)
- `deploy-cloudrun.sh` (new)
- `unified_app.py` (modified - PORT variable)
- `templates/*.html` (modified - removed icons, styled disabled buttons)

---

## 🎨 UI Improvements Completed

1. ✅ Removed all emoji icons from entire UI
2. ✅ Styled non-functional buttons as disabled:
   - TTS Audio (Coming Soon)
   - Voice Input (Coming Soon)
   - AI Search (Coming Soon)
3. ✅ Consistent purple gradient theme
4. ✅ Professional, clean appearance

---

## 🔄 Update Existing Deployment

If you already have a deployment and just want to update it:

```bash
# Quick update
gcloud builds submit --tag gcr.io/isl-translator-492416/isl-translator
gcloud run deploy isl-translator --image gcr.io/isl-translator-492416/isl-translator --region us-central1
```

---

## 📊 Monitor Your App

### Check Service Status
```bash
gcloud run services describe isl-translator --region us-central1 --format=yaml
```

### View Metrics
```bash
# CPU usage
gcloud monitoring time-series list \
    --filter='metric.type="run.googleapis.com/container/cpu/utilizations"' \
    --format=json

# Memory usage
gcloud monitoring time-series list \
    --filter='metric.type="run.googleapis.com/container/memory/utilizations"' \
    --format=json
```

### Get Service URL
```bash
gcloud run services describe isl-translator --region us-central1 --format='value(status.url)'
```

---

## 🆘 Need Help?

### Common Issues

1. **"Permission denied" error**
   ```bash
   gcloud auth login
   gcloud config set project isl-translator-492416
   ```

2. **"Image not found" error**
   - Rebuild image: `gcloud builds submit --tag gcr.io/isl-translator-492416/isl-translator`

3. **"Service unavailable" error**
   - Check logs: `gcloud run logs tail isl-translator --region us-central1`
   - Increase memory/CPU in deployment command

4. **Videos still not loading**
   - Verify Dockerfile includes: `COPY knowledge_base/ knowledge_base/`
   - Check .dockerignore doesn't exclude videos
   - Test locally first: `docker build -f Dockerfile.cloudrun -t test . && docker run -p 8080:8080 test`

### Contact & Resources
- Cloud Run Docs: https://cloud.google.com/run/docs
- Flask Docs: https://flask.palletsprojects.com/
- Project GitHub: [Your repo URL]

---

## ✅ Deployment Checklist

Before deploying:
- [ ] Commit all changes to git
- [ ] Test locally: `python unified_app.py`
- [ ] Verify videos load locally: http://localhost:5000/videos/hello.mp4
- [ ] Check requirements.txt is up to date
- [ ] Review Dockerfile.cloudrun
- [ ] Run deployment script or manual commands
- [ ] Test deployed URL
- [ ] Check logs for errors
- [ ] Verify all features work

After deploying:
- [ ] Test main page loads
- [ ] Test video playback
- [ ] Test search functionality
- [ ] Test sign recognition
- [ ] Monitor logs for 5-10 minutes
- [ ] Share URL with users

---

## 🎯 Next Steps

1. Deploy the updated application
2. Verify videos load correctly
3. Monitor performance
4. Implement additional improvements from DEPLOYMENT_FIXES.md
5. Gather user feedback

Good luck with your deployment! 🚀
