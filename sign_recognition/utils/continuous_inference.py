import collections

class ContinuousSignRecognizer:
    """Fallback per-segment recognizer for continuous sign recognition."""
    def __init__(self, recognizer=None):
        self.recognizer = recognizer
        self.sessions = {}

    def create_session(self, session_id, confidence_threshold=0.45, dedup_window=3, cooldown=0.8):
        self.sessions[session_id] = {
            'sentence': [],
            'last_prediction': None,
            'confidence_threshold': confidence_threshold
        }

    def get_session(self, session_id):
        return self.sessions.get(session_id)

    def process_video_segment(self, session_id, video_path):
        import unified_app
        session = self.sessions.get(session_id)
        if not session:
            return {'error': 'Invalid session'}
            
        success, text, confidence = unified_app.run_include_inference(video_path)
        
        if success and confidence >= session['confidence_threshold']:
            # Simple dedup mechanism
            if text != session['last_prediction'] and text != '':
                session['sentence'].append(text)
                session['last_prediction'] = text
                
        return {
            'sentence': ' '.join(session['sentence']),
            'latest_segment': text if success else '',
            'confidence': confidence if success else 0.0
        }

class CTCContinuousRecognizer:
    """Stub for CTC recognizer."""
    def __init__(self, model_path, metadata_path, device='cpu'):
        pass
        
    def create_session(self, session_id):
        pass
        
    def get_session(self, session_id):
        return {}
        
    def process_video_segment(self, session_id, video_path):
        return {'sentence': '', 'latest_segment': '', 'confidence': 0.0}
