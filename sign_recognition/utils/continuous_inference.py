import time
import collections

class ContinuousSignRecognizer:
    """Fallback per-segment recognizer for continuous sign recognition."""
    def __init__(self, recognizer=None):
        self.recognizer = recognizer
        self.sessions = {}

    def create_session(self, session_id, confidence_threshold=0.45, dedup_window=3, cooldown=0.8):
        self.sessions[session_id] = ContinuousSession(
            session_id, confidence_threshold, dedup_window, cooldown
        )

    def get_session(self, session_id):
        return self.sessions.get(session_id)

    def process_video_segment(self, session_id, video_path):
        session = self.get_session(session_id)
        if not session:
            return {'error': 'Invalid session'}
        return session.process_segment(video_path)

    def process_frame(self, session_id, frame_bytes):
        # Frame-by-frame is harder for this model, stub it or implement if needed
        return {'error': 'Frame-by-frame not implemented for legacy recognizer'}

    def end_session(self, session_id):
        session = self.sessions.pop(session_id, None)
        if session:
            return {
                'sentence': session.get_sentence_text(),
                'tokens_count': len(session.tokens)
            }
        return None

class ContinuousSession:
    def __init__(self, session_id, confidence_threshold, dedup_window, cooldown):
        self.session_id = session_id
        self.confidence_threshold = confidence_threshold
        self.dedup_window = dedup_window
        self.cooldown = cooldown
        self.tokens = []  # List of {sign, confidence, timestamp}
        self.last_sign_time = 0
        self.start_time = time.time()

    def process_segment(self, video_path):
        import unified_app
        try:
            # 1. Extract keypoints
            pk_x, pk_y, h1_x, h1_y, h2_x, h2_y = unified_app._extract_keypoints_from_video(video_path)
            
            # 2. Convert to tensor
            tensor = unified_app._keypoints_to_tensor(pk_x, pk_y, h1_x, h1_y, h2_x, h2_y)
            
            # 3. Run inference
            label, confidence = unified_app.run_include_inference(tensor)
            
            action = 'none'
            if label and confidence >= self.confidence_threshold:
                # Simple dedup mechanism: don't repeat the same sign twice in a row within a short window
                current_time = time.time()
                is_duplicate = False
                if self.tokens:
                    last_token = self.tokens[-1]
                    if last_token['sign'] == label and (current_time - last_token['wall_time'] < 2.0):
                        is_duplicate = True
                
                if not is_duplicate:
                    self.tokens.append({
                        'sign': label,
                        'confidence': float(confidence),
                        'timestamp': current_time - self.start_time,
                        'wall_time': current_time
                    })
                    action = 'added'
                    
            return {
                'action': action,
                'tokens': self.get_serializable_tokens(),
                'latest_segment': label if label else '',
                'confidence': float(confidence)
            }
        except Exception as e:
            return {
                'error': str(e),
                'tokens': self.get_serializable_tokens()
            }

    def get_serializable_tokens(self):
        # Remove wall_time for JSON serialization
        return [{k: v for k, v in t.items() if k != 'wall_time'} for t in self.tokens]

    def undo_last(self):
        if self.tokens:
            self.tokens.pop()
        return {'action': 'undo', 'tokens': self.get_serializable_tokens()}

    def reset(self):
        self.tokens = []
        self.start_time = time.time()
        return {'action': 'reset', 'tokens': []}

    def get_sentence_text(self):
        return ' '.join([t['sign'] for t in self.tokens])

class CTCContinuousRecognizer:
    """Stub for CTC recognizer."""
    def __init__(self, model_path, metadata_path, device='cpu'):
        self.sessions = {}
        
    def create_session(self, session_id):
        self.sessions[session_id] = {'tokens': []}
        
    def get_session(self, session_id):
        return self.sessions.get(session_id)
        
    def process_video_segment(self, session_id, video_path):
        return {'sentence': '', 'latest_segment': '', 'confidence': 0.0, 'tokens': []}

    def reset_session(self, session_id):
        if session_id in self.sessions:
            self.sessions[session_id]['tokens'] = []
        return {'action': 'reset', 'tokens': []}

    def end_session(self, session_id):
        self.sessions.pop(session_id, None)
        return {'sentence': '', 'tokens_count': 0}
