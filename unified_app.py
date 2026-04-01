#!/usr/bin/env python3
"""
ISL RAG Translator - Unified Application
Complete text-to-sign and sign-to-speech translation system
"""

import os
import json
import string
import uuid
import logging
import tempfile
import re
from datetime import datetime
import numpy as np
import torch
import faiss
from sentence_transformers import SentenceTransformer
from flask import Flask, render_template, jsonify, request, send_from_directory
from werkzeug.utils import secure_filename
from gtts import gTTS

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Initialize Flask App
app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
TEMP_AUDIO_FOLDER = 'temp_audio'
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'webm', 'MOV'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max

# Create directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TEMP_AUDIO_FOLDER, exist_ok=True)

# Global variables for text-to-sign
model = None
metadata_list = None
known_phrases_sorted = None
text_to_file_map = None
synonym_dict = None

# Global variables for FAISS semantic search
faiss_index = None
index_map = None
FAISS_SCORE_THRESHOLD = 0.4  # Minimum similarity score for semantic matches

# Global variables for sign-to-speech
sign_recognizer = None
sign_model_loaded = False

# Global variable for continuous (SignGemma-style / CTC) recognition
continuous_recognizer = None
ctc_continuous_recognizer = None

def load_text_to_sign_components():
    """Load AI model and all necessary mappings for text-to-sign translation."""
    global model, metadata_list, known_phrases_sorted, text_to_file_map, synonym_dict
    
    logger.info("🚀 Loading text-to-sign AI components...")
    
    try:
        # Load sentence transformer model
        model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("✅ Sentence transformer model loaded")
        
        # Load metadata
        meta_path = 'knowledge_base/metadata.json'
        if not os.path.exists(meta_path):
            raise FileNotFoundError(f"Metadata file not found at {meta_path}")
        
        with open(meta_path, 'r', encoding='utf-8') as f:
            metadata_list = json.load(f)
        
        logger.info(f"📹 Found {len(metadata_list)} available video phrases")
        
        # Create helper mappings
        known_phrases_sorted = sorted([item['text'].lower() for item in metadata_list], key=len, reverse=True)
        text_to_file_map = {item['text'].lower(): item['file'] for item in metadata_list}
        
        # Load synonyms (optional)
        synonym_path = 'knowledge_base/synonym_dict.json'
        synonym_dict = {}
        if os.path.exists(synonym_path):
            with open(synonym_path, 'r', encoding='utf-8') as f:
                synonym_dict = json.load(f)
            logger.info(f"📝 Loaded {len(synonym_dict)} synonym mappings")
        
        # Load FAISS index for semantic search fallback
        faiss_path = 'video_index.faiss'
        index_map_path = 'index_map.json'
        if os.path.exists(faiss_path) and os.path.exists(index_map_path):
            faiss_index = faiss.read_index(faiss_path)
            with open(index_map_path, 'r') as f:
                index_map = json.load(f)
            index_map = {int(k): v for k, v in index_map.items()}
            logger.info(f"🔍 FAISS index loaded with {faiss_index.ntotal} vectors")
        else:
            logger.warning("⚠️ FAISS index not found - run setup_database.py to enable semantic search")
        
        logger.info("✅ Text-to-sign components loaded successfully!")
        return True
        
    except Exception as e:
        logger.error(f"Failed to load text-to-sign components: {e}")
        return False

def load_sign_to_speech_components():
    """Load the CNN+LSTM model for sign-to-speech translation."""
    global sign_recognizer, sign_model_loaded

    logger.info("Loading CNN+LSTM sign recognition model...")

    try:
        import sys
        import json as _json

        project_root = os.path.dirname(os.path.abspath(__file__))
        if project_root not in sys.path:
            sys.path.insert(0, project_root)

        from INCLUDE.models.lstm import LSTM
        from INCLUDE.configs import LstmConfig, CnnConfig

        model_path = os.path.join(project_root, 'INCLUDE', 'cnn_augs_lstm.pth')
        label_map_path = os.path.join(project_root, 'INCLUDE', 'label_maps', 'label_map_include.json')

        if not os.path.exists(model_path):
            logger.error(f"Model file not found: {model_path}")
            sign_model_loaded = False
            return False

        with open(label_map_path, 'r') as f:
            label_map = _json.load(f)

        idx_to_label = {v: k for k, v in label_map.items()}
        n_classes = len(label_map)  # 263

        config = LstmConfig()
        config.input_size = CnnConfig.output_dim  # 1280 CNN features

        model_obj = LSTM(config=config, n_classes=n_classes)
        checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
        state = checkpoint['model'] if 'model' in checkpoint else checkpoint
        state = {k.replace('module.', ''): v for k, v in state.items()}
        model_obj.load_state_dict(state)
        model_obj.eval()

        sign_recognizer = {
            'model': model_obj,
            'idx_to_label': idx_to_label,
            'label_map': label_map,
            'n_classes': n_classes,
            'model_type': 'cnn_lstm',
        }
        sign_model_loaded = True
        logger.info(f"CNN+LSTM model loaded — {n_classes} classes, score={checkpoint.get('score', 'N/A')}")
        return True

    except Exception as e:
        logger.error(f"Failed to load CNN+LSTM model: {e}")
        sign_model_loaded = False
        return False

        if not os.path.exists(model_path):
            logger.error(f"Model file not found: {model_path}")
            sign_model_loaded = False
            return False

        with open(label_map_path, 'r') as f:
            label_map = _json.load(f)

        idx_to_label = {v: k for k, v in label_map.items()}
        n_classes = len(label_map)  # 263

        config = TransformerConfig(size='small')
        model_obj = Transformer(config=config, n_classes=n_classes)

        checkpoint = torch.load(model_path, map_location='cpu', weights_only=False)
        state = checkpoint['model'] if 'model' in checkpoint else checkpoint
        state = {k.replace('module.', ''): v for k, v in state.items()}
        model_obj.load_state_dict(state)
        model_obj.eval()

        sign_recognizer = {
            'model': model_obj,
            'idx_to_label': idx_to_label,
            'label_map': label_map,
            'n_classes': n_classes,
        }
        sign_model_loaded = True
        logger.info(f"INCLUDE transformer loaded — {n_classes} classes, score={checkpoint.get('score', 'N/A')}")
        return True

    except Exception as e:
        logger.error(f"Failed to load INCLUDE model: {e}")
        sign_model_loaded = False
        return False

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# ==================== INCLUDE50 INFERENCE PIPELINE ====================

def _extract_keypoints_from_video(video_path):
    """Extract mediapipe keypoints from a video file.
    Returns (pose_x, pose_y, hand1_x, hand1_y, hand2_x, hand2_y) as lists-of-lists."""
    import sys
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from INCLUDE.generate_keypoints import (
        _USE_LEGACY, process_landmarks, process_hand_keypoints,
        process_pose_keypoints, swap_hands,
    )
    import cv2
    import mediapipe as mp

    pose_x, pose_y = [], []
    h1_x, h1_y, h2_x, h2_y = [], [], [], []

    if _USE_LEGACY:
        mp_hands = mp.solutions.hands
        mp_pose = mp.solutions.pose
        hands = mp_hands.Hands(static_image_mode=False, max_num_hands=2,
                               min_detection_confidence=0.5, min_tracking_confidence=0.5)
        pose_det = mp_pose.Pose(static_image_mode=False,
                                min_detection_confidence=0.5, min_tracking_confidence=0.5)
        cap = cv2.VideoCapture(video_path)
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h_res = hands.process(rgb)
            p_res = pose_det.process(rgb)

            if p_res.pose_landmarks:
                px, py = process_landmarks(p_res.pose_landmarks)
                pose_x.append(px[:25]); pose_y.append(py[:25])
            else:
                pose_x.append([np.nan]*25); pose_y.append([np.nan]*25)

            _h1x, _h1y, _h2x, _h2y = process_hand_keypoints(h_res)
            h1_x.append(_h1x if _h1x else [np.nan]*21)
            h1_y.append(_h1y if _h1y else [np.nan]*21)
            h2_x.append(_h2x if _h2x else [np.nan]*21)
            h2_y.append(_h2y if _h2y else [np.nan]*21)
        cap.release()
        hands.close()
        pose_det.close()
    else:
        from INCLUDE.generate_keypoints import (
            _HAND_MODEL, _POSE_MODEL,
        )
        from mediapipe.tasks import python as mp_tasks
        from mediapipe.tasks import python
        from mediapipe.tasks.python import vision as mp_vision

        hand_opts = mp_vision.HandLandmarkerOptions(
            base_options=mp_tasks.BaseOptions(model_asset_path=_HAND_MODEL),
            num_hands=2, min_hand_detection_confidence=0.5,
            min_tracking_confidence=0.5,
            running_mode=mp_vision.RunningMode.VIDEO,
        )
        pose_opts = mp_vision.PoseLandmarkerOptions(
            base_options=mp_tasks.BaseOptions(model_asset_path=_POSE_MODEL),
            min_pose_detection_confidence=0.5, min_tracking_confidence=0.5,
            running_mode=mp_vision.RunningMode.VIDEO,
        )
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        n = 0
        with mp_vision.HandLandmarker.create_from_options(hand_opts) as hd, \
             mp_vision.PoseLandmarker.create_from_options(pose_opts) as pd:
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                ts = int(n * 1000 / fps)
                h_res = hd.detect_for_video(mp_img, ts)
                p_res = pd.detect_for_video(mp_img, ts)

                if p_res.pose_landmarks:
                    lms = p_res.pose_landmarks[0]
                    pose_x.append([lm.x for lm in lms][:25])
                    pose_y.append([lm.y for lm in lms][:25])
                else:
                    pose_x.append([np.nan]*25); pose_y.append([np.nan]*25)

                _h1x = _h1y = _h2x = _h2y = None
                if h_res.hand_landmarks:
                    _h1x = [lm.x for lm in h_res.hand_landmarks[0]]
                    _h1y = [lm.y for lm in h_res.hand_landmarks[0]]
                    if len(h_res.hand_landmarks) > 1:
                        _h2x = [lm.x for lm in h_res.hand_landmarks[1]]
                        _h2y = [lm.y for lm in h_res.hand_landmarks[1]]
                h1_x.append(_h1x if _h1x else [np.nan]*21)
                h1_y.append(_h1y if _h1y else [np.nan]*21)
                h2_x.append(_h2x if _h2x else [np.nan]*21)
                h2_y.append(_h2y if _h2y else [np.nan]*21)
                n += 1
        cap.release()

    return pose_x, pose_y, h1_x, h1_y, h2_x, h2_y


def _extract_keypoints_from_frame(frame_bgr):
    """Extract mediapipe keypoints from a single BGR frame (numpy array).
    Returns same structure as _extract_keypoints_from_video but for 1 frame."""
    import sys
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from INCLUDE.generate_keypoints import _USE_LEGACY, process_landmarks, process_hand_keypoints
    import mediapipe as mp
    import cv2

    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)

    if _USE_LEGACY:
        mp_hands = mp.solutions.hands
        mp_pose = mp.solutions.pose
        with mp_hands.Hands(static_image_mode=True, max_num_hands=2,
                            min_detection_confidence=0.5) as hands, \
             mp_pose.Pose(static_image_mode=True,
                          min_detection_confidence=0.5) as pose_det:
            h_res = hands.process(rgb)
            p_res = pose_det.process(rgb)

        if p_res.pose_landmarks:
            px, py = process_landmarks(p_res.pose_landmarks)
            pose_x = [px[:25]]; pose_y = [py[:25]]
        else:
            pose_x = [[np.nan]*25]; pose_y = [[np.nan]*25]

        _h1x, _h1y, _h2x, _h2y = process_hand_keypoints(h_res)
        h1_x = [_h1x if _h1x else [np.nan]*21]
        h1_y = [_h1y if _h1y else [np.nan]*21]
        h2_x = [_h2x if _h2x else [np.nan]*21]
        h2_y = [_h2y if _h2y else [np.nan]*21]
    else:
        from INCLUDE.generate_keypoints import _HAND_MODEL, _POSE_MODEL
        from mediapipe.tasks import python as mp_tasks
        from mediapipe.tasks.python import vision as mp_vision

        hand_opts = mp_vision.HandLandmarkerOptions(
            base_options=mp_tasks.BaseOptions(model_asset_path=_HAND_MODEL),
            num_hands=2, running_mode=mp_vision.RunningMode.IMAGE,
        )
        pose_opts = mp_vision.PoseLandmarkerOptions(
            base_options=mp_tasks.BaseOptions(model_asset_path=_POSE_MODEL),
            running_mode=mp_vision.RunningMode.IMAGE,
        )
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        with mp_vision.HandLandmarker.create_from_options(hand_opts) as hd, \
             mp_vision.PoseLandmarker.create_from_options(pose_opts) as pd:
            h_res = hd.detect(mp_img)
            p_res = pd.detect(mp_img)

        if p_res.pose_landmarks:
            lms = p_res.pose_landmarks[0]
            pose_x = [[lm.x for lm in lms][:25]]
            pose_y = [[lm.y for lm in lms][:25]]
        else:
            pose_x = [[np.nan]*25]; pose_y = [[np.nan]*25]

        _h1x = _h1y = _h2x = _h2y = None
        if h_res.hand_landmarks:
            _h1x = [lm.x for lm in h_res.hand_landmarks[0]]
            _h1y = [lm.y for lm in h_res.hand_landmarks[0]]
            if len(h_res.hand_landmarks) > 1:
                _h2x = [lm.x for lm in h_res.hand_landmarks[1]]
                _h2y = [lm.y for lm in h_res.hand_landmarks[1]]
        h1_x = [_h1x if _h1x else [np.nan]*21]
        h1_y = [_h1y if _h1y else [np.nan]*21]
        h2_x = [_h2x if _h2x else [np.nan]*21]
        h2_y = [_h2y if _h2y else [np.nan]*21]

    return pose_x, pose_y, h1_x, h1_y, h2_x, h2_y


def _keypoints_to_tensor(pose_x, pose_y, h1_x, h1_y, h2_x, h2_y,
                          max_frame_len=200, frame_length=1080, frame_width=1920):
    """Convert raw keypoint lists to a normalised, padded tensor — exactly matching dataset.py."""
    import pandas as pd

    def combine_xy(x, y):
        # x,y from video extractor: (n_frames, n_landmarks) — same as JSON format
        x = np.array(x, dtype=np.float32)  # (n_frames, n_landmarks) — NO transpose
        y = np.array(y, dtype=np.float32)
        n_frames, n_lm = x.shape
        x = x.reshape((n_frames, n_lm, 1))
        y = y.reshape((n_frames, n_lm, 1))
        return np.concatenate([x, y], axis=-1)  # (n_frames, n_lm, 2)

    def interpolate(arr):
        arr_x = pd.DataFrame(arr[:, :, 0]).interpolate(method='linear', limit_direction='both').to_numpy()
        arr_y = pd.DataFrame(arr[:, :, 1]).interpolate(method='linear', limit_direction='both').to_numpy()
        if np.count_nonzero(~np.isnan(arr_x)) == 0:
            arr_x = np.zeros_like(arr_x)
        if np.count_nonzero(~np.isnan(arr_y)) == 0:
            arr_y = np.zeros_like(arr_y)
        arr_x = arr_x * frame_width
        arr_y = arr_y * frame_length
        return np.stack([arr_x, arr_y], axis=-1)

    pose = interpolate(combine_xy(pose_x, pose_y))   # (T, 25, 2)
    h1   = interpolate(combine_xy(h1_x,   h1_y))     # (T, 21, 2)
    h2   = interpolate(combine_xy(h2_x,   h2_y))     # (T, 21, 2)

    pose_flat = pose.reshape(-1, 50).astype(np.float32)
    h1_flat   = h1.reshape(-1, 42).astype(np.float32)
    h2_flat   = h2.reshape(-1, 42).astype(np.float32)

    data = np.concatenate([pose_flat, h1_flat, h2_flat], axis=-1)  # (T, 134)

    T = data.shape[0]
    if T >= max_frame_len:
        data = data[:max_frame_len]
    else:
        data = np.pad(data, ((0, max_frame_len - T), (0, 0)), 'constant')

    mean = data.mean()
    std  = data.std() + 1e-8
    data = (data - mean) / std
    # replace any remaining NaN/inf with 0
    data = np.nan_to_num(data, nan=0.0, posinf=0.0, neginf=0.0)

    return torch.FloatTensor(data).unsqueeze(0)  # (1, T, 134)


def _extract_cnn_features_from_video(video_path, max_frames=200):
    """Extract MobileNetV2 features from video frames for CNN+LSTM inference."""
    import cv2
    from torchvision import transforms

    transform = transforms.Compose([
        transforms.ToPILImage(),
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ])

    import sys
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    from INCLUDE.models import CNN
    from INCLUDE.configs import CnnConfig

    config = CnnConfig()
    cnn = CNN(config)
    cnn.eval()

    cap = cv2.VideoCapture(video_path)
    features = []
    with torch.no_grad():
        while cap.isOpened() and len(features) < max_frames:
            ret, frame = cap.read()
            if not ret:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            tensor = transform(rgb).unsqueeze(0)
            feat = cnn(tensor).cpu().numpy().squeeze()
            features.append(feat)
    cap.release()
    return np.array(features, dtype=np.float32)  # (T, 1280)


def _cnn_features_to_tensor(features, max_frame_len=200):
    """Pad/truncate CNN features and return tensor."""
    T = features.shape[0]
    if T >= max_frame_len:
        features = features[:max_frame_len]
    else:
        features = np.pad(features, ((0, max_frame_len - T), (0, 0)), 'constant')
    return torch.FloatTensor(features).unsqueeze(0)  # (1, T, 1280)


def run_include_inference(tensor):
    """Run the CNN+LSTM model on a prepared tensor.
    Returns (label_string, confidence_float) or (None, confidence) if below threshold."""
    if not sign_model_loaded or sign_recognizer is None:
        raise RuntimeError("CNN+LSTM model not loaded")

    model_obj    = sign_recognizer['model']
    idx_to_label = sign_recognizer['idx_to_label']

    with torch.no_grad():
        logits = model_obj(tensor)
        probs  = torch.softmax(logits, dim=-1)
        conf, pred = probs.max(dim=-1)

    confidence = conf.item()
    if np.isnan(confidence) or np.isinf(confidence):
        confidence = 0.0

    label = idx_to_label[pred.item()]
    return label, confidence



# ==================== NLP PREPROCESSING ====================

# Common English contractions → expansions
CONTRACTION_MAP = {
    "i'm": "i am", "i've": "i have", "i'll": "i will", "i'd": "i would",
    "you're": "you are", "you've": "you have", "you'll": "you will", "you'd": "you would",
    "he's": "he is", "she's": "she is", "it's": "it is",
    "we're": "we are", "we've": "we have", "we'll": "we will", "we'd": "we would",
    "they're": "they are", "they've": "they have", "they'll": "they will", "they'd": "they would",
    "that's": "that is", "who's": "who is", "what's": "what is",
    "there's": "there is", "here's": "here is", "where's": "where is",
    "can't": "can not", "won't": "will not", "don't": "do not",
    "doesn't": "does not", "didn't": "did not", "isn't": "is not",
    "aren't": "are not", "wasn't": "was not", "weren't": "were not",
    "haven't": "have not", "hasn't": "has not", "hadn't": "had not",
    "couldn't": "could not", "wouldn't": "would not", "shouldn't": "should not",
    "let's": "let us", "how's": "how is", "who've": "who have",
}

# Articles that ISL does not sign — safe to remove
ISL_DROP_WORDS = {'a', 'an', 'the'}


def nlp_preprocess(text):
    """
    NLP preprocessing pipeline for ISL-friendly matching:
      1. Expand contractions  ("what's" → "what is")
      2. Remove articles       ("the", "a", "an")
    This runs BEFORE punctuation cleanup so apostrophes are still intact.
    """
    processed = text.lower()

    # --- Step 1: expand contractions (regex word-boundary safe) ---
    for contraction, expansion in CONTRACTION_MAP.items():
        pattern = re.compile(re.escape(contraction), re.IGNORECASE)
        processed = pattern.sub(expansion, processed)

    # --- Step 2: remove ISL-irrelevant articles ---
    words = processed.split()
    words = [w for w in words if w not in ISL_DROP_WORDS]
    processed = ' '.join(words)

    return processed


# ==================== FAISS SEMANTIC SEARCH ====================

def faiss_semantic_search(text, top_k=3, threshold=None):
    """
    Encode *text* with the sentence-transformer and search the FAISS index.
    Returns a list of dicts: [{file, text, score, l2_distance}, ...]
    Only results with score >= threshold are returned.
    """
    if threshold is None:
        threshold = FAISS_SCORE_THRESHOLD

    if faiss_index is None or model is None:
        return []

    try:
        query_embedding = model.encode([text], convert_to_numpy=True)
        distances, indices = faiss_index.search(query_embedding, top_k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx == -1:  # FAISS pads with -1
                continue
            filename = index_map.get(int(idx))
            if not filename:
                continue

            # Convert L2 distance to 0-1 similarity score
            similarity = 1.0 / (1.0 + float(dist))

            if similarity < threshold:
                continue

            phrase_text = os.path.splitext(filename)[0].lower()
            results.append({
                'file': filename,
                'text': phrase_text,
                'score': round(similarity, 3),
                'l2_distance': round(float(dist), 3),
            })
        return results

    except Exception as e:
        logger.error(f"FAISS search error: {e}")
        return []


def rebuild_faiss_index():
    """
    Rebuild the FAISS index from current metadata.json.
    Called after new videos are contributed so semantic search stays in sync.
    """
    global faiss_index, index_map

    if model is None or metadata_list is None:
        logger.warning("Cannot rebuild FAISS: model or metadata not loaded")
        return False

    try:
        texts = [item['text'] for item in metadata_list]
        filenames = [item['file'] for item in metadata_list]

        embeddings = model.encode(texts, convert_to_numpy=True)
        dim = embeddings.shape[1]

        new_index = faiss.IndexFlatL2(dim)
        new_index = faiss.IndexIDMap(new_index)
        new_index.add_with_ids(embeddings, np.arange(len(texts)))

        faiss.write_index(new_index, 'video_index.faiss')

        new_map = {i: fn for i, fn in enumerate(filenames)}
        with open('index_map.json', 'w') as f:
            json.dump(new_map, f)

        faiss_index = new_index
        index_map = {int(k): v for k, v in new_map.items()}

        logger.info(f"🔄 FAISS index rebuilt with {faiss_index.ntotal} vectors")
        return True

    except Exception as e:
        logger.error(f"FAISS rebuild failed: {e}")
        return False


# ==================== ENHANCED SEARCH PIPELINE ====================

def get_video_playlist(query_text):
    """
    Enhanced search pipeline:
      1. NLP preprocessing   — expand contractions, remove articles
      2. Synonym expansion   — apply synonym_dict
      3. Greedy exact match  — longest-first phrase matching
      4. FAISS fallback      — semantic search for unmatched words
      5. Hybrid scoring      — exact=1.0, semantic=model score
    Returns a playlist sorted by position in the original query.
    """
    logger.info(f"🔍 Searching for: '{query_text}'")
    playlist = []

    # --- Step 1: NLP preprocessing (before punctuation cleanup!) ---
    preprocessed = nlp_preprocess(query_text)
    logger.info(f"📝 After NLP preprocessing: '{preprocessed}'")

    # --- Step 2: clean punctuation ---
    space_maker = str.maketrans(string.punctuation, ' ' * len(string.punctuation))
    remaining_query = preprocessed.translate(space_maker).strip()
    # Collapse multiple spaces
    remaining_query = re.sub(r'\s+', ' ', remaining_query)
    original_query = remaining_query  # Keep copy for position tracking

    # --- Step 3: synonym expansion ---
    for synonym, replacement in synonym_dict.items():
        if synonym in remaining_query:
            remaining_query = remaining_query.replace(synonym, replacement)
            original_query = original_query.replace(synonym, replacement)
            logger.info(f"📝 Applied synonym: '{synonym}' → '{replacement}'")

    # --- Step 4: greedy longest-match exact matching ---
    for phrase in known_phrases_sorted:
        start_idx = 0
        while start_idx < len(remaining_query):
            start_idx = remaining_query.find(phrase, start_idx)
            if start_idx == -1:
                break

            end_idx = start_idx + len(phrase)
            if (start_idx == 0 or remaining_query[start_idx - 1] == ' ') and \
               (end_idx == len(remaining_query) or remaining_query[end_idx] == ' '):

                original_position = original_query.find(phrase)
                logger.info(f"✅ Exact match: '{phrase}' at position {original_position}")
                filename = text_to_file_map[phrase]

                audio_filename = os.path.splitext(filename)[0].replace(' ', '_') + '.mp3'
                audio_path = os.path.join('knowledge_base/generated_audio', audio_filename)
                has_audio = os.path.exists(audio_path)

                playlist.append({
                    "file": filename,
                    "text": phrase,
                    "score": 1.0,
                    "match_type": "exact",
                    "has_audio_file": has_audio,
                    "audio_url": f"/audio/{audio_filename}" if has_audio else None,
                    "position": original_position
                })

                remaining_query = remaining_query[:start_idx] + ' ' * len(phrase) + remaining_query[end_idx:]
                original_query = original_query.replace(phrase, ' ' * len(phrase), 1)
                start_idx += len(phrase)
            else:
                start_idx += 1

    # --- Step 5: FAISS semantic fallback for unmatched words ---
    unmatched_words = [w for w in remaining_query.split() if len(w) >= 2]
    if unmatched_words and faiss_index is not None:
        logger.info(f"🔎 FAISS fallback for unmatched: {unmatched_words}")
        already_matched = {item['text'] for item in playlist}

        for word in unmatched_words:
            results = faiss_semantic_search(word, top_k=1)
            for r in results:
                if r['text'] not in already_matched:
                    audio_fn = os.path.splitext(r['file'])[0].replace(' ', '_') + '.mp3'
                    audio_path = os.path.join('knowledge_base/generated_audio', audio_fn)
                    has_audio = os.path.exists(audio_path)

                    pos = query_text.lower().find(word)
                    playlist.append({
                        "file": r['file'],
                        "text": r['text'],
                        "score": r['score'],
                        "match_type": "semantic",
                        "original_word": word,
                        "has_audio_file": has_audio,
                        "audio_url": f"/audio/{audio_fn}" if has_audio else None,
                        "position": pos if pos != -1 else len(query_text)
                    })
                    already_matched.add(r['text'])
                    logger.info(f"🧠 Semantic match: '{word}' → '{r['text']}' (score: {r['score']})")

    # --- Step 6: sort by position to maintain word order ---
    playlist.sort(key=lambda x: x.get('position', 0))

    logger.info(f"📜 Final playlist: {[(p['text'], p['match_type'], p['score']) for p in playlist]}")
    return playlist

def get_or_create_audio(text):
    """Return audio URL for text — uses cached file if exists, generates once if not."""
    safe = text.lower().replace(' ', '_').replace('(', '').replace(')', '')
    # Check knowledge_base first
    kb_path = os.path.join('knowledge_base/generated_audio', f'{safe}.mp3')
    if os.path.exists(kb_path):
        return f'/audio/{safe}.mp3'
    # Check permanent cache
    cache_path = os.path.join('temp_audio', f'{safe}.mp3')
    if not os.path.exists(cache_path):
        try:
            from gtts import gTTS
            gTTS(text=text, lang='en', slow=False).save(cache_path)
        except Exception:
            return None
    return f'/temp-audio/{safe}.mp3'


def process_text_to_sign(input_text):
    """Process input text and return matched phrases with audio URLs"""
    global known_phrases_sorted, text_to_file_map

    input_text = input_text.lower()
    remaining_query = input_text
    playlist = []

    for phrase in known_phrases_sorted:
        while phrase in remaining_query:
            # Check word boundary
            start_idx = remaining_query.find(phrase)
            end_idx = start_idx + len(phrase)

            if (start_idx == 0 or remaining_query[start_idx - 1] == ' ') and \
               (end_idx == len(remaining_query) or remaining_query[end_idx] == ' '):
                logger.info(f"✅ Match found: '{phrase}'")
                filename = text_to_file_map[phrase]

                # Check if audio file exists
                # Replace spaces with underscores for audio filename
                audio_filename = os.path.splitext(filename)[0].replace(' ', '_') + '.mp3'
                audio_path = os.path.join('knowledge_base/generated_audio', audio_filename)
                has_audio = os.path.exists(audio_path)

                playlist.append({
                    "file": filename,
                    "text": phrase,
                    "score": 1.0,
                    "match_type": "exact",
                    "has_audio_file": has_audio,
                    "audio_url": f"/audio/{audio_filename}" if has_audio else None
                })

                logger.info(f"🎵 Added to playlist: {phrase} -> {audio_filename}")

                # Remove matched phrase from remaining query
                remaining_query = remaining_query[:start_idx] + remaining_query[end_idx:]
            else:
                break

    return playlist

# ==================== ROUTES ====================

@app.route('/')
def index():
    """Main text-to-sign page"""
    return render_template('index.html')

@app.route('/sign-recognition')
def sign_recognition():
    """Sign-to-speech recognition page"""
    return render_template('sign_recognition.html', model_loaded=sign_model_loaded)

@app.route('/live-sign-recognition')
def live_sign_recognition():
    """Live camera-based sign recognition page"""
    return render_template('live_sign_recognition.html', model_loaded=sign_model_loaded)

@app.route('/continuous-sign-recognition')
def continuous_sign_recognition_page():
    """Continuous (SignGemma-style) sign recognition page"""
    return render_template('continuous_sign_recognition.html', model_loaded=sign_model_loaded)

@app.route('/recognize-live-sign', methods=['POST'])
def recognize_live_sign():
    """Handle live sign recognition — CNN+LSTM needs video sequence, use /upload-sign-video."""
    return jsonify({
        'success': False,
        'error': 'Use the Record button to capture a 3-second video for recognition'
    }), 400

# ==================== TEXT-TO-SIGN ROUTES ====================

@app.route('/search', methods=['POST'])
def search():
    """Search API endpoint for text-to-sign"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        
        if not query:
            return jsonify({"error": "Empty query"}), 400
        
        playlist = get_video_playlist(query)
        
        return jsonify({
            "playlist": playlist,
            "query": query,
            "total_results": len(playlist)
        })
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/videos/<path:filename>')
def serve_video(filename):
    """Serve video files"""
    return send_from_directory('knowledge_base/videos', filename)

@app.route('/audio/<path:filename>')
def serve_audio(filename):
    """Serve audio files with enhanced error handling"""
    audio_path = os.path.join('knowledge_base/generated_audio', filename)

    if not os.path.exists(audio_path):
        logger.error(f"Audio file not found: {audio_path}")
        return jsonify({"error": "Audio file not found"}), 404

    try:
        return send_from_directory('knowledge_base/generated_audio', filename, mimetype='audio/mpeg')
    except Exception as e:
        logger.error(f"Failed to serve audio file: {e}")
        return jsonify({"error": "Failed to serve audio file"}), 500

# ==================== SIGN-TO-SPEECH ROUTES ====================

@app.route('/recognize-from-keypoints', methods=['POST'])
def recognize_from_keypoints():
    """Receive keypoints extracted by MediaPipe JS and run inference directly."""
    if not sign_model_loaded:
        return jsonify({'success': False, 'error': 'Model not loaded'}), 503
    try:
        data = request.get_json()
        pose_x  = data['pose_x'];  pose_y  = data['pose_y']
        hand1_x = data['hand1_x']; hand1_y = data['hand1_y']
        hand2_x = data['hand2_x']; hand2_y = data['hand2_y']

        tensor = _keypoints_to_tensor(pose_x, pose_y, hand1_x, hand1_y, hand2_x, hand2_y)
        predicted_text, confidence = run_include_inference(tensor)
        logger.info(f"Keypoint inference: {predicted_text} ({confidence:.2f})")

        if predicted_text is None:
            return jsonify({'success': True, 'recognized_text': None,
                           'message': 'Low confidence — try again with clearer sign'})

        return jsonify({
            'success': True,
            'recognized_text': predicted_text,
            'confidence': float(confidence),
            'audio_url': get_or_create_audio(predicted_text),
        })
    except Exception as e:
        logger.error(f"Keypoint inference failed: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/upload-sign-video', methods=['POST'])
def upload_sign_video():
    """Handle sign video upload and recognition using INCLUDE50 transformer."""
    start_time = datetime.now()

    if not sign_model_loaded:
        return jsonify({'success': False, 'error': 'Sign recognition model not loaded'}), 503

    try:
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400

        file = request.files['video']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400

        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Please upload MP4, AVI, MOV, or WEBM files.'}), 400

        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], f"{uuid.uuid4().hex}_{filename}")
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        logger.info(f"Video saved: {file_path} ({file_size} bytes)")

        try:
            features = _extract_cnn_features_from_video(file_path)
            n_frames = len(features)
            logger.info(f"CNN features extracted: {n_frames} frames")
            if n_frames == 0:
                return jsonify({'success': False, 'error': 'No frames extracted from video'}), 400
            tensor = _cnn_features_to_tensor(features)
            predicted_text, confidence = run_include_inference(tensor)
            logger.info(f"Sign recognized: {predicted_text} ({confidence:.2f})")
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)

        if predicted_text is None:
            return jsonify({
                'success': True,
                'recognized_text': None,
                'confidence': float(confidence),
                'message': f'Low confidence ({confidence:.1%}) — ensure hands are clearly visible and sign is from INCLUDE50 dataset',
                'is_demo': False
            })

        processing_time = (datetime.now() - start_time).total_seconds()

        return jsonify({
            'success': True,
            'recognized_text': predicted_text,
            'confidence': float(confidence),
            'audio_url': get_or_create_audio(predicted_text),
            'processing_time': processing_time,
            'message': f'Sign recognized: "{predicted_text}"',
            'is_demo': False
        })

    except Exception as e:
        logger.error(f"Upload processing failed: {e}")
        return jsonify({'success': False, 'error': 'Sign recognition failed', 'details': str(e)}), 500

@app.route('/temp-audio/<filename>')
def serve_temp_audio(filename):
    """Serve temporary audio files"""
    return send_from_directory(TEMP_AUDIO_FOLDER, filename)

# ==================== API ROUTES ====================

@app.route('/api/stats')
def get_stats():
    """Get system statistics"""
    try:
        videos = len([f for f in os.listdir('knowledge_base/videos') if f.endswith('.mp4')])
        audio_files = len([f for f in os.listdir('knowledge_base/generated_audio') if f.endswith('.mp3')])
        
        return jsonify({
            "total_videos": videos,
            "total_audio_files": audio_files,
            "metadata_entries": len(metadata_list) if metadata_list else 0,
            "synonym_mappings": len(synonym_dict) if synonym_dict else 0,
            "text_to_sign_status": "ready" if model else "not_loaded",
            "sign_to_speech_status": "ready" if sign_model_loaded else "demo_mode"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/sign-recognition-status')
def sign_recognition_status():
    """Get sign recognition system status"""
    available_signs = []
    if sign_model_loaded and sign_recognizer:
        available_signs = list(sign_recognizer['idx_to_label'].values())

    return jsonify({
        'model_loaded': sign_model_loaded,
        'available_signs': available_signs,
        'n_classes': len(available_signs),
        'model': 'INCLUDE50 Transformer (small)',
        'status': 'ready' if sign_model_loaded else 'not_loaded'
    })

# ==================== CONTRIBUTION ROUTES ====================

@app.route('/contribute')
def contribute_page():
    """Contribution page for users to upload new ISL videos"""
    return render_template('contribute.html')

@app.route('/api/contribute-video', methods=['POST'])
def contribute_video():
    """Handle video contribution from users"""
    try:
        # Get form data
        phrase = request.form.get('phrase', '').strip().lower()
        description = request.form.get('description', '').strip()
        contributor_name = request.form.get('contributor_name', 'Anonymous').strip()
        
        if not phrase:
            return jsonify({'error': 'Phrase is required'}), 400
        
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400
        
        file = request.files['video']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Please upload MP4, AVI, MOV, or WEBM files.'}), 400
        
        # Create safe filename
        safe_phrase = phrase.replace(' ', '_')
        file_extension = os.path.splitext(file.filename)[1]
        video_filename = f"{phrase}{file_extension}"
        
        # Save video to knowledge base
        video_path = os.path.join('knowledge_base/videos', video_filename)
        file.save(video_path)
        
        logger.info(f"Video contributed: {video_filename} by {contributor_name}")
        
        # Generate TTS audio for the phrase
        try:
            audio_filename = f"{safe_phrase}.mp3"
            audio_path = os.path.join('knowledge_base/generated_audio', audio_filename)
            
            tts = gTTS(text=phrase, lang='en', slow=False)
            tts.save(audio_path)
            
            logger.info(f"Generated audio: {audio_filename}")
        except Exception as e:
            logger.error(f"Failed to generate audio: {e}")
        
        # Update metadata.json
        try:
            metadata_path = 'knowledge_base/metadata.json'
            
            # Load existing metadata
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            else:
                metadata = []
            
            # Check if phrase already exists
            existing_entry = next((item for item in metadata if item.get('text', '').lower() == phrase), None)
            
            if existing_entry:
                # Update existing entry
                existing_entry['file'] = video_filename
                existing_entry['text'] = phrase
                existing_entry['description'] = description or existing_entry.get('description', '')
                existing_entry['updated_by'] = contributor_name
                existing_entry['updated_at'] = datetime.now().isoformat()
                message = f"Updated existing video for '{phrase}'"
            else:
                # Add new entry
                new_entry = {
                    'file': video_filename,
                    'text': phrase,
                    'description': description,
                    'contributor': contributor_name,
                    'contributed_at': datetime.now().isoformat(),
                    'category': 'user_contributed'
                }
                metadata.append(new_entry)
                message = f"Added new video for '{phrase}'"
            
            # Save updated metadata
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info(f"Updated metadata.json: {message}")
            
            # Reload text-to-sign components to include new video
            load_text_to_sign_components()
            
            # Rebuild FAISS index so semantic search includes the new video
            rebuild_faiss_index()
            
            return jsonify({
                'success': True,
                'message': message,
                'phrase': phrase,
                'video_file': video_filename,
                'audio_file': audio_filename,
                'contributor': contributor_name
            })
            
        except Exception as e:
            logger.error(f"Failed to update metadata: {e}")
            return jsonify({
                'success': False,
                'error': 'Failed to update metadata',
                'details': str(e)
            }), 500
            
    except Exception as e:
        logger.error(f"Video contribution failed: {e}")
        return jsonify({
            'success': False,
            'error': 'Video contribution failed',
            'details': str(e)
        }), 500

@app.route('/api/rebuild-index', methods=['POST'])
def api_rebuild_index():
    """Rebuild FAISS index from current metadata (useful after adding new videos)"""
    try:
        success = rebuild_faiss_index()
        if success:
            return jsonify({"success": True, "message": f"FAISS index rebuilt with {faiss_index.ntotal} vectors"})
        return jsonify({"success": False, "message": "Rebuild failed — check logs"}), 500
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==================== CONTINUOUS RECOGNITION API ====================

@app.route('/api/continuous/start', methods=['POST'])
def continuous_start():
    """Create a new continuous-recognition session.

    Prefers the CTC-based recognizer if a CTC model exists, otherwise
    falls back to the legacy per-segment classifier with dedup.
    """
    global continuous_recognizer, ctc_continuous_recognizer

    data = request.get_json() or {}
    session_id = uuid.uuid4().hex

    # Try CTC recognizer first
    ctc_model_path = 'sign_recognition/trained_models/best_ctc_model.pth'
    ctc_meta_path = 'sign_recognition/trained_models/ctc_metadata.json'

    if os.path.exists(ctc_model_path) and os.path.exists(ctc_meta_path):
        if ctc_continuous_recognizer is None:
            from sign_recognition.utils.continuous_inference import CTCContinuousRecognizer
            ctc_continuous_recognizer = CTCContinuousRecognizer(
                model_path=ctc_model_path,
                metadata_path=ctc_meta_path,
                device='cpu',
            )
        ctc_continuous_recognizer.create_session(session_id)
        return jsonify({'session_id': session_id, 'mode': 'ctc'})

    # Fallback to legacy
    if continuous_recognizer is None:
        from sign_recognition.utils.continuous_inference import ContinuousSignRecognizer
        continuous_recognizer = ContinuousSignRecognizer(
            recognizer=sign_recognizer if sign_model_loaded else None
        )

    continuous_recognizer.create_session(
        session_id,
        confidence_threshold=data.get('confidence_threshold', 0.45),
        dedup_window=data.get('dedup_window', 3),
        cooldown=data.get('cooldown', 0.8),
    )
    return jsonify({'session_id': session_id, 'mode': 'legacy'})


@app.route('/api/continuous/segment', methods=['POST'])
def continuous_segment():
    """Receive a video segment, classify it, update the session sentence."""
    session_id = request.form.get('session_id', '')

    # Check CTC recognizer first
    if ctc_continuous_recognizer and ctc_continuous_recognizer.get_session(session_id):
        if 'video' not in request.files:
            return jsonify({'error': 'No video segment provided'}), 400
        video_file = request.files['video']
        temp_path = os.path.join(UPLOAD_FOLDER, f'seg_{uuid.uuid4().hex}.webm')
        video_file.save(temp_path)
        try:
            result = ctc_continuous_recognizer.process_video_segment(session_id, temp_path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        return jsonify(result)

    # Legacy fallback
    if continuous_recognizer is None:
        return jsonify({'error': 'No continuous recognizer initialised'}), 400

    if not continuous_recognizer.get_session(session_id):
        return jsonify({'error': 'Invalid session'}), 400

    if 'video' not in request.files:
        return jsonify({'error': 'No video segment provided'}), 400

    video_file = request.files['video']
    temp_path = os.path.join(UPLOAD_FOLDER, f'seg_{uuid.uuid4().hex}.webm')
    video_file.save(temp_path)

    try:
        result = continuous_recognizer.process_video_segment(session_id, temp_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return jsonify(result)


@app.route('/api/continuous/frame', methods=['POST'])
def continuous_frame():
    """Receive a single JPEG frame, classify it, update the session."""
    session_id = request.form.get('session_id', '')

    if 'image' not in request.files:
        return jsonify({'error': 'No image provided'}), 400
    frame_bytes = request.files['image'].read()

    # Check CTC recognizer first
    if ctc_continuous_recognizer and ctc_continuous_recognizer.get_session(session_id):
        result = ctc_continuous_recognizer.process_frame(session_id, frame_bytes)
        return jsonify(result)

    # Legacy fallback
    if continuous_recognizer is None:
        return jsonify({'error': 'No continuous recognizer initialised'}), 400
    if not continuous_recognizer.get_session(session_id):
        return jsonify({'error': 'Invalid session'}), 400

    result = continuous_recognizer.process_frame(session_id, frame_bytes)
    return jsonify(result)


@app.route('/api/continuous/undo', methods=['POST'])
def continuous_undo():
    """Undo the last recognized sign in the session sentence."""
    data = request.get_json() or {}
    session_id = data.get('session_id', '')

    # CTC sessions don't support granular undo — reset instead
    if ctc_continuous_recognizer and ctc_continuous_recognizer.get_session(session_id):
        return jsonify(ctc_continuous_recognizer.reset_session(session_id))

    if continuous_recognizer and continuous_recognizer.get_session(session_id):
        return jsonify(continuous_recognizer.get_session(session_id).undo_last())
    return jsonify({'error': 'Invalid session'}), 400


@app.route('/api/continuous/reset', methods=['POST'])
def continuous_reset():
    """Clear the session sentence and start fresh."""
    data = request.get_json() or {}
    session_id = data.get('session_id', '')

    if ctc_continuous_recognizer and ctc_continuous_recognizer.get_session(session_id):
        return jsonify(ctc_continuous_recognizer.reset_session(session_id))

    if continuous_recognizer and continuous_recognizer.get_session(session_id):
        return jsonify(continuous_recognizer.get_session(session_id).reset())
    return jsonify({'error': 'Invalid session'}), 400


@app.route('/api/continuous/stop', methods=['POST'])
def continuous_stop():
    """End a continuous-recognition session and return final stats."""
    data = request.get_json() if request.content_type and 'json' in request.content_type else {}
    if not data:
        try:
            data = json.loads(request.get_data(as_text=True))
        except Exception:
            data = {}
    session_id = data.get('session_id', '')

    # Try CTC first
    if ctc_continuous_recognizer:
        stats = ctc_continuous_recognizer.end_session(session_id)
        if stats:
            return jsonify({'success': True, **stats})

    if continuous_recognizer:
        stats = continuous_recognizer.end_session(session_id)
        if stats:
            return jsonify({'success': True, **stats})
    return jsonify({'error': 'Invalid session'}), 400


@app.route('/api/continuous/speak', methods=['POST'])
def continuous_speak():
    """Generate TTS audio for the current session sentence."""
    data = request.get_json() or {}
    session_id = data.get('session_id', '')

    sentence = None
    # CTC session
    if ctc_continuous_recognizer and ctc_continuous_recognizer.get_session(session_id):
        sentence = ctc_continuous_recognizer.get_session(session_id).get_sentence_text()
    # Legacy session
    elif continuous_recognizer and continuous_recognizer.get_session(session_id):
        sentence = continuous_recognizer.get_session(session_id).get_sentence_text()
    else:
        return jsonify({'error': 'Invalid session'}), 400

    if sentence:
        audio_filename = generate_tts_audio(sentence)
        return jsonify({
            'sentence': sentence,
            'audio_url': f'/temp-audio/{audio_filename}' if audio_filename else None
        })
    return jsonify({'sentence': '', 'audio_url': None})


@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "text_to_sign_loaded": model is not None and metadata_list is not None,
        "sign_to_speech_loaded": sign_model_loaded,
        "faiss_index_loaded": faiss_index is not None,
        "faiss_vectors": faiss_index.ntotal if faiss_index else 0,
        "timestamp": datetime.now().isoformat()
    })

# ==================== MAIN ====================

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🎯 ISL RAG TRANSLATOR - UNIFIED SYSTEM")
    print("   Complete Text-to-Sign & Sign-to-Speech Translation")
    print("="*70)
    
    # Load text-to-sign components
    print("🔄 Loading text-to-sign components...")
    text_to_sign_loaded = load_text_to_sign_components()
    
    if text_to_sign_loaded:
        print(f"✅ Text-to-sign ready with {len(metadata_list)} videos")
    else:
        print("❌ Text-to-sign failed to load")
    
    # Load sign-to-speech components
    print("🔄 Loading sign-to-speech components...")
    sign_to_speech_loaded = load_sign_to_speech_components()
    
    if sign_to_speech_loaded:
        print("✅ Sign-to-speech model loaded")
    else:
        print("🎭 Sign-to-speech running in demo mode")
    
    print("\n" + "="*70)
    print("🚀 SYSTEM READY!")
    print("="*70)
    print("📍 Main URL: http://127.0.0.1:5000")
    print("🔤 Text-to-Sign: http://127.0.0.1:5000/")
    print("🎥 Sign-to-Speech: http://127.0.0.1:5000/sign-recognition")
    print("✋ Continuous: http://127.0.0.1:5000/continuous-sign-recognition")
    print("📊 System Stats: http://127.0.0.1:5000/api/stats")
    print("💚 Health Check: http://127.0.0.1:5000/health")
    print("="*70)
    print("⏹️ Press Ctrl+C to stop the server")
    print("="*70)
    
    # Start Flask app
    app.run(host='0.0.0.0', port=5000, debug=False)