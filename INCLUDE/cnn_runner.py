"""
Extracts MobileNetV2 CNN features directly from video frames.
Each video frame is resized to 224x224 and passed through MobileNetV2.
"""
import os
import glob
import numpy as np
import torch
import cv2
from tqdm import tqdm
from torchvision import transforms

from models import CNN
from configs import CnnConfig
from generate_keypoints import load_file

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

TRANSFORM = transforms.Compose([
    transforms.ToPILImage(),
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406],
                         std=[0.229, 0.224, 0.225]),
])


def extract_cnn_features_from_video(video_path, cnn_model, max_frames=200):
    """Extract MobileNetV2 features from actual video frames."""
    cap = cv2.VideoCapture(video_path)
    features = []
    frame_count = 0

    cnn_model.eval()
    with torch.no_grad():
        while cap.isOpened() and frame_count < max_frames:
            ret, frame = cap.read()
            if not ret:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            tensor = TRANSFORM(rgb).unsqueeze(0).to(device)
            feat = cnn_model(tensor).cpu().numpy().squeeze()  # (1280,)
            features.append(feat)
            frame_count += 1

    cap.release()
    if len(features) == 0:
        return None, None

    features = np.array(features, dtype=np.float32)  # (T, 1280)
    label = video_path.replace('\\', '/').split('/')[-2]
    label = ''.join([c for c in label if c.isalpha()]).lower()
    return features, label


def save_cnn_features(args):
    """Extract CNN features from videos and save as .npy — resumable."""
    config = CnnConfig()
    cnn = CNN(config).to(device)
    cnn.eval()
    print(f"CNN model: {config.model}, output_dim: {config.output_dim}")

    include_dir = getattr(args, 'include_dir', None) or getattr(args, 'data_dir', None)

    for split in ['train', 'val', 'test']:
        out_dir = os.path.join(args.data_dir, f"{args.dataset}_{split}_cnn_features")
        os.makedirs(out_dir, exist_ok=True)

        txt_file = f"train_test_paths/{args.dataset}_{split}.txt"
        if not os.path.exists(txt_file):
            print(f"Skipping {split} — {txt_file} not found")
            continue

        paths = load_file(txt_file, include_dir)
        print(f"\nProcessing {split}: {len(paths)} videos → {out_dir}")

        processed = skipped = errors = 0
        for path in tqdm(paths, desc=split):
            label = path.replace('\\', '/').split('/')[-2]
            label = ''.join([c for c in label if c.isalpha()]).lower()
            uid = '_'.join([label, os.path.splitext(os.path.basename(path))[0]])
            out_file = os.path.join(out_dir, f"{uid}.npy")

            if os.path.exists(out_file):
                skipped += 1
                continue

            if not os.path.exists(path):
                continue

            try:
                features, _ = extract_cnn_features_from_video(path, cnn)
                if features is not None:
                    np.save(out_file, features)
                    processed += 1
            except Exception as e:
                errors += 1

        done = len(glob.glob(os.path.join(out_dir, "*.npy")))
        print(f"  {split}: {processed} new | {skipped} skipped | {errors} errors | {done} total")
