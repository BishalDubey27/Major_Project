"""
Debug script: compare pre-extracted keypoints vs live extraction from same video.
Run: python debug_pipeline.py path/to/MVI_2988.MOV
"""
import sys, os, torch, json, numpy as np, pandas as pd
sys.path.insert(0, '.')
sys.path.insert(0, 'INCLUDE')

from INCLUDE.models.transformer import Transformer
from INCLUDE.configs import TransformerConfig

# Load model
cp = torch.load('INCLUDE/augs_transformer (1).pth', map_location='cpu', weights_only=False)
with open('INCLUDE/label_maps/label_map_include50.json') as f:
    label_map = json.load(f)
idx_to_label = {v: k for k, v in label_map.items()}
config = TransformerConfig(size='small')
model = Transformer(config=config, n_classes=50)
model.load_state_dict(cp['model'])
model.eval()

def infer(data):
    data = np.pad(data, ((0, 200-data.shape[0]),(0,0)), 'constant')
    mean, std = data.mean(), data.std()+1e-8
    data = np.nan_to_num((data-mean)/std, nan=0.0)
    tensor = torch.FloatTensor(data).unsqueeze(0)
    with torch.no_grad():
        probs = torch.softmax(model(tensor), dim=-1)
        conf, pred = probs.max(dim=-1)
    return idx_to_label[pred.item()], round(conf.item(), 3)

def combine_xy(x, y):
    x, y = np.array(x, dtype=float), np.array(y, dtype=float)
    _, length = x.shape
    return np.concatenate([x.reshape(-1,length,1), y.reshape(-1,length,1)], axis=-1).astype(np.float32)

def interpolate(arr, fw=1920, fl=1080):
    ax = pd.DataFrame(arr[:,:,0]).interpolate(method='linear',limit_direction='both').to_numpy()
    ay = pd.DataFrame(arr[:,:,1]).interpolate(method='linear',limit_direction='both').to_numpy()
    if np.count_nonzero(~np.isnan(ax))==0: ax=np.zeros_like(ax)
    if np.count_nonzero(~np.isnan(ay))==0: ay=np.zeros_like(ay)
    return np.stack([ax*fw, ay*fl], axis=-1)

# ── Test 1: pre-extracted keypoints ──────────────────────────────────
print("=== Test 1: Pre-extracted keypoints ===")
row = pd.read_json('INCLUDE/keypoints/include50_test_keypoints/bird_MVI_2988.json', typ='series')
pose = interpolate(combine_xy(row.pose_x, row.pose_y))
h1   = interpolate(combine_xy(row.hand1_x, row.hand1_y))
h2   = interpolate(combine_xy(row.hand2_x, row.hand2_y))
data = np.concatenate([pose.reshape(-1,50), h1.reshape(-1,42), h2.reshape(-1,42)], axis=-1)
label, conf = infer(data)
print(f"Prediction: {label}, Confidence: {conf}")
print(f"pose_x[0][:3]: {np.array(row.pose_x, dtype=float)[0][:3]}")
print(f"n_frames: {row.n_frames}")

# ── Test 2: live extraction from video ────────────────────────────────
if len(sys.argv) > 1:
    video_path = sys.argv[1]
    print(f"\n=== Test 2: Live extraction from {video_path} ===")
    from unified_app import _extract_keypoints_from_video, _keypoints_to_tensor
    pose_x, pose_y, h1_x, h1_y, h2_x, h2_y = _extract_keypoints_from_video(video_path)
    print(f"n_frames: {len(pose_x)}")
    print(f"pose_x[0][:3]: {np.array(pose_x[0], dtype=float)[:3]}")
    print(f"hand1 NaN count: {sum(1 for f in h1_x for v in f if np.isnan(float(v)))}")

    # Use same preprocessing as pre-extracted
    pose = interpolate(combine_xy(np.array(pose_x).T.tolist(), np.array(pose_y).T.tolist()))
    h1   = interpolate(combine_xy(np.array(h1_x).T.tolist(),   np.array(h1_y).T.tolist()))
    h2   = interpolate(combine_xy(np.array(h2_x).T.tolist(),   np.array(h2_y).T.tolist()))
    data = np.concatenate([pose.reshape(-1,50), h1.reshape(-1,42), h2.reshape(-1,42)], axis=-1)
    label, conf = infer(data)
    print(f"Prediction (same preprocessing): {label}, Confidence: {conf}")

    # Use app's _keypoints_to_tensor
    tensor = _keypoints_to_tensor(pose_x, pose_y, h1_x, h1_y, h2_x, h2_y)
    with torch.no_grad():
        probs = torch.softmax(model(tensor), dim=-1)
        c, p = probs.max(dim=-1)
    print(f"Prediction (app pipeline): {idx_to_label[p.item()]}, Confidence: {round(c.item(),3)}")
else:
    print("\nProvide video path as argument to test live extraction")
    print("Usage: python debug_pipeline.py path/to/video.MOV")
