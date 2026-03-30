"""
Extracts MobileNetV2 CNN features from keypoint-rendered frames.
Each video is rendered as a sequence of skeleton images, then
MobileNetV2 extracts 1280-dim features per frame.
"""
import os
import json
import glob
import numpy as np
import torch
import cv2
from tqdm import tqdm
from torch.utils import data
from torchvision import transforms

from models import CNN
from configs import CnnConfig
from generate_keypoints import load_file


device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ImageNet normalization
TRANSFORM = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
])


def render_skeleton_frame(pose_x, pose_y, hand1_x, hand1_y, hand2_x, hand2_y,
                           width=224, height=224):
    """Render a single skeleton frame as an RGB image."""
    img = np.zeros((height, width, 3), dtype=np.uint8)

    def draw_points(xs, ys, color):
        for x, y in zip(xs, ys):
            if not (np.isnan(x) or np.isnan(y)):
                cx, cy = int(x * width), int(y * height)
                cv2.circle(img, (cx, cy), 3, color, -1)

    draw_points(pose_x,  pose_y,  (0, 212, 255))   # cyan — pose
    draw_points(hand1_x, hand1_y, (0, 230, 118))   # green — left hand
    draw_points(hand2_x, hand2_y, (255, 109, 0))   # orange — right hand
    return img


def extract_cnn_features_from_keypoints(kp_file, cnn_model, max_frames=200):
    """Load a keypoint JSON and extract CNN features for each frame."""
    import pandas as pd

    row = pd.read_json(kp_file, typ='series')
    pose_x  = np.array(row.pose_x,  dtype=float)   # (n_frames, 25)
    pose_y  = np.array(row.pose_y,  dtype=float)
    hand1_x = np.array(row.hand1_x, dtype=float)   # (n_frames, 21)
    hand1_y = np.array(row.hand1_y, dtype=float)
    hand2_x = np.array(row.hand2_x, dtype=float)
    hand2_y = np.array(row.hand2_y, dtype=float)

    n_frames = pose_x.shape[0]
    features = []

    cnn_model.eval()
    with torch.no_grad():
        for i in range(min(n_frames, max_frames)):
            frame = render_skeleton_frame(
                pose_x[i], pose_y[i],
                hand1_x[i], hand1_y[i],
                hand2_x[i], hand2_y[i],
            )
            tensor = TRANSFORM(frame).unsqueeze(0).to(device)
            feat = cnn_model(tensor).cpu().numpy().squeeze()  # (1280,)
            features.append(feat)

    features = np.array(features, dtype=np.float32)  # (T, 1280)
    return features, row.label


def save_cnn_features(args):
    """Extract CNN features from all keypoint files and save as .npy."""
    config = CnnConfig()
    cnn = CNN(config).to(device)
    cnn.eval()
    print(f"CNN model: {config.model}, output_dim: {config.output_dim}")

    for split in ['train', 'val', 'test']:
        kp_dir  = os.path.join(args.data_dir, f"{args.dataset}_{split}_keypoints")
        out_dir = os.path.join(args.data_dir, f"{args.dataset}_{split}_cnn_features")
        os.makedirs(out_dir, exist_ok=True)

        kp_files = sorted(glob.glob(os.path.join(kp_dir, "*.json")))
        print(f"\nProcessing {split}: {len(kp_files)} files → {out_dir}")

        for kp_file in tqdm(kp_files, desc=split):
            uid = os.path.splitext(os.path.basename(kp_file))[0]
            out_file = os.path.join(out_dir, f"{uid}.npy")

            if os.path.exists(out_file):
                continue  # skip already done

            try:
                features, label = extract_cnn_features_from_keypoints(kp_file, cnn)
                np.save(out_file, features)
            except Exception as e:
                print(f"  Error {kp_file}: {e}")

        done = len(glob.glob(os.path.join(out_dir, "*.npy")))
        print(f"  {split}: {done} feature files saved")
