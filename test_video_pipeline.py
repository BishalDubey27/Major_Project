"""
Full end-to-end test: extract keypoints from a video file and compare
with pre-extracted keypoints to find any mismatch.

Usage: python test_video_pipeline.py path/to/video.MOV label
Example: python test_video_pipeline.py "C:/path/to/Animals/4. Bird/MVI_2988.MOV" bird
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

def combine_xy_json(x, y):
    """For pre-extracted JSON: already (n_frames, n_landmarks)"""
    x, y = np.array(x, dtype=float), np.array(y, dtype=float)
    _, length = x.shape
    return np.concatenate([x.reshape(-1,length,1), y.reshape(-1,length,1)], axis=-1).astype(np.float32)

def interpolate(arr, fw=1920, fl=1080):
    ax = pd.DataFrame(arr[:,:,0]).interpolate(method='linear',limit_direction='both').to_numpy()
    ay = pd.DataFrame(arr[:,:,1]).interpolate(method='linear',limit_direction='both').to_numpy()
    if np.count_nonzero(~np.isnan(ax))==0: ax=np.zeros_like(ax)
    if np.count_nonzero(~np.isnan(ay))==0: ay=np.zeros_like(ay)
    return np.stack([ax*fw, ay*fl], axis=-1)

def infer_from_data(data):
    data = np.pad(data, ((0,200-data.shape[0]),(0,0)), 'constant')
    mean, std = data.mean(), data.std()+1e-8
    data = np.nan_to_num((data-mean)/std, nan=0.0)
    tensor = torch.FloatTensor(data).unsqueeze(0)
    with torch.no_grad():
        probs = torch.softmax(model(tensor), dim=-1)
        conf, pred = probs.max(dim=-1)
    return idx_to_label[pred.item()], round(conf.item(), 3)

# ── Test all keypoint files ──────────────────────────────────────────
import glob
print("=== Testing all pre-extracted keypoints ===")
files = glob.glob('INCLUDE/keypoints/include50_test_keypoints/*.json')
correct = 0
for f in files:
    row = pd.read_json(f, typ='series')
    true_label = row.label
    pose = interpolate(combine_xy_json(row.pose_x, row.pose_y))
    h1   = interpolate(combine_xy_json(row.hand1_x, row.hand1_y))
    h2   = interpolate(combine_xy_json(row.hand2_x, row.hand2_y))
    data = np.concatenate([pose.reshape(-1,50), h1.reshape(-1,42), h2.reshape(-1,42)], axis=-1)
    label, conf = infer_from_data(data)
    if label == true_label: correct += 1
print(f"Keypoint accuracy: {correct}/{len(files)} = {correct/len(files)*100:.1f}%")

# ── Test live extraction if video provided ───────────────────────────
if len(sys.argv) >= 3:
    video_path = sys.argv[1]
    true_label = sys.argv[2]
    print(f"\n=== Testing live extraction: {video_path} (true: {true_label}) ===")

    from unified_app import _extract_keypoints_from_video, _keypoints_to_tensor

    pose_x, pose_y, h1_x, h1_y, h2_x, h2_y = _extract_keypoints_from_video(video_path)
    print(f"Frames extracted: {len(pose_x)}")
    print(f"pose_x[0][:3]: {np.array(pose_x[0], dtype=float)[:3]}")

    # Method 1: app's _keypoints_to_tensor
    tensor = _keypoints_to_tensor(pose_x, pose_y, h1_x, h1_y, h2_x, h2_y)
    with torch.no_grad():
        probs = torch.softmax(model(tensor), dim=-1)
        conf, pred = probs.max(dim=-1)
    print(f"App pipeline: {idx_to_label[pred.item()]} ({conf.item():.3f}) — {'CORRECT' if idx_to_label[pred.item()]==true_label else 'WRONG'}")

    # Method 2: same as JSON preprocessing
    def combine_xy_live(x, y):
        x = np.array(x, dtype=np.float32)  # (n_frames, n_landmarks)
        y = np.array(y, dtype=np.float32)
        n_frames, n_lm = x.shape
        return np.concatenate([x.reshape(n_frames,n_lm,1), y.reshape(n_frames,n_lm,1)], axis=-1)

    pose = interpolate(combine_xy_live(pose_x, pose_y))
    h1   = interpolate(combine_xy_live(h1_x, h1_y))
    h2   = interpolate(combine_xy_live(h2_x, h2_y))
    data = np.concatenate([pose.reshape(-1,50), h1.reshape(-1,42), h2.reshape(-1,42)], axis=-1)
    label, conf = infer_from_data(data)
    print(f"JSON-style pipeline: {label} ({conf}) — {'CORRECT' if label==true_label else 'WRONG'}")

    # Compare first frame values
    print(f"\nLive pose_x[0][:3]: {np.array(pose_x[0])[:3]}")
    vid_num = os.path.splitext(os.path.basename(video_path))[0].split("_")[-1]
    json_path = f'INCLUDE/keypoints/include50_test_keypoints/{true_label}_MVI_{vid_num}.json'
    if os.path.exists(json_path):
        row = pd.read_json(json_path, typ='series')
        print(f"JSON  pose_x[0][:3]: {np.array(row.pose_x, dtype=float)[0][:3]}")
    else:
        print(f"No matching JSON found at {json_path}")
else:
    print("\nTo test a specific video:")
    print("python test_video_pipeline.py path/to/video.MOV label")
    print("Example: python test_video_pipeline.py 'C:/path/Animals/4. Bird/MVI_2988.MOV' bird")
