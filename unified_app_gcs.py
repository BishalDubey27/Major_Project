"""
Modified video/audio serving routes for Google Cloud Storage
Add these lines at the top of unified_app.py after imports
"""

# Add this to the imports section at the top
import os

# Add this configuration after app initialization
USE_GCS = os.environ.get('USE_GCS', 'false').lower() == 'true'
GCS_BUCKET = os.environ.get('GCS_BUCKET', 'isl-translator-492416-videos')
GCS_BASE_URL = f"https://storage.googleapis.com/{GCS_BUCKET}"

# Replace the @app.route('/videos/<path:filename>') function with this:
@app.route('/videos/<path:filename>')
def serve_video(filename):
    """Serve video files from GCS or local storage"""
    if USE_GCS:
        # Redirect to GCS public URL
        from flask import redirect
        gcs_url = f"{GCS_BASE_URL}/videos/{filename}"
        return redirect(gcs_url)
    else:
        # Serve from local storage
        return send_from_directory('knowledge_base/videos', filename)

# Replace the @app.route('/audio/<path:filename>') function with this:
@app.route('/audio/<path:filename>')
def serve_audio(filename):
    """Serve audio files from GCS or local storage"""
    if USE_GCS:
        # Redirect to GCS public URL
        from flask import redirect
        gcs_url = f"{GCS_BASE_URL}/audio/{filename}"
        return redirect(gcs_url)
    else:
        # Serve from local storage
        audio_path = os.path.join('knowledge_base/generated_audio', filename)
        if not os.path.exists(audio_path):
            logger.error(f"Audio file not found: {audio_path}")
            return jsonify({"error": "Audio file not found"}), 404
        try:
            return send_from_directory('knowledge_base/generated_audio', filename, mimetype='audio/mpeg')
        except Exception as e:
            logger.error(f"Failed to serve audio file: {e}")
            return jsonify({"error": "Failed to serve audio file"}), 500
