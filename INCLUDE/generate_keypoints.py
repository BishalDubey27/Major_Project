import os
import json
import multiprocessing
import argparse
import os.path
import cv2
from tqdm.auto import tqdm
from joblib import Parallel, delayed
import numpy as np
import gc
import warnings

# Support both old (<=0.9) and new (>=0.10) mediapipe APIs
try:
    import mediapipe as mp
    _USE_LEGACY = hasattr(mp, 'solutions')
except ImportError:
    raise ImportError("mediapipe is not installed")

if not _USE_LEGACY:
    from mediapipe.tasks import python as mp_tasks
    from mediapipe.tasks.python import vision as mp_vision
    import urllib.request, tempfile

    # Use local task files shipped with the project (Windows-compatible paths)
    _SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    _HAND_MODEL = os.path.join(_SCRIPT_DIR, 'hand_landmarker.task')
    _POSE_MODEL = os.path.join(_SCRIPT_DIR, 'pose_landmarker_lite.task')
    if not os.path.isfile(_HAND_MODEL):
        urllib.request.urlretrieve(
            'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task',
            _HAND_MODEL)
    if not os.path.isfile(_POSE_MODEL):
        urllib.request.urlretrieve(
            'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task',
            _POSE_MODEL)

def process_landmarks(landmarks):
    x_list, y_list = [], []
    for landmark in landmarks.landmark:
        x_list.append(landmark.x)
        y_list.append(landmark.y)
    return x_list, y_list


def process_hand_keypoints(results):
    hand1_x, hand1_y, hand2_x, hand2_y = [], [], [], []

    if results.multi_hand_landmarks is not None:
        if len(results.multi_hand_landmarks) > 0:
            hand1 = results.multi_hand_landmarks[0]
            hand1_x, hand1_y = process_landmarks(hand1)

        if len(results.multi_hand_landmarks) > 1:
            hand2 = results.multi_hand_landmarks[1]
            hand2_x, hand2_y = process_landmarks(hand2)

    return hand1_x, hand1_y, hand2_x, hand2_y


def process_pose_keypoints(results):
    pose = results.pose_landmarks
    pose_x, pose_y = process_landmarks(pose)
    return pose_x, pose_y


def swap_hands(left_wrist, right_wrist, hand, input_hand):
    left_wrist_x, left_wrist_y = left_wrist
    right_wrist_x, right_wrist_y = right_wrist
    hand_x, hand_y = hand

    left_dist = (left_wrist_x - hand_x) ** 2 + (left_wrist_y - hand_y) ** 2
    right_dist = (right_wrist_x - hand_x) ** 2 + (right_wrist_y - hand_y) ** 2

    if left_dist < right_dist and input_hand == "h2":
        return True

    if right_dist < left_dist and input_hand == "h1":
        return True

    return False


def _process_video_legacy(path, save_dir):
    """Original implementation using old mp.solutions API."""
    hands = mp.solutions.hands.Hands(
        min_detection_confidence=0.5, min_tracking_confidence=0.5
    )
    pose = mp.solutions.pose.Pose(
        min_detection_confidence=0.5, min_tracking_confidence=0.5
    )

    pose_points_x, pose_points_y = [], []
    hand1_points_x, hand1_points_y = [], []
    hand2_points_x, hand2_points_y = [], []

    label = path.split("/")[-2]
    label = "".join([i for i in label if i.isalpha()]).lower()
    uid = os.path.splitext(os.path.basename(path))[0]
    uid = "_".join([label, uid])
    n_frames = 0
    if not os.path.isfile(path):
        warnings.warn(path + " file not found")
    cap = cv2.VideoCapture(path)
    while cap.isOpened():
        ret, image = cap.read()
        if not ret:
            break
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        hand_results = hands.process(image)
        pose_results = pose.process(image)

        hand1_x, hand1_y, hand2_x, hand2_y = process_hand_keypoints(hand_results)
        pose_x, pose_y = process_pose_keypoints(pose_results)

        if len(hand1_x) > 0 and len(hand2_x) == 0:
            if swap_hands(
                left_wrist=(pose_x[15], pose_y[15]),
                right_wrist=(pose_x[16], pose_y[16]),
                hand=(hand1_x[0], hand1_y[0]),
                input_hand="h1",
            ):
                hand1_x, hand1_y, hand2_x, hand2_y = hand2_x, hand2_y, hand1_x, hand1_y
        elif len(hand1_x) == 0 and len(hand2_x) > 0:
            if swap_hands(
                left_wrist=(pose_x[15], pose_y[15]),
                right_wrist=(pose_x[16], pose_y[16]),
                hand=(hand2_x[0], hand2_y[0]),
                input_hand="h2",
            ):
                hand1_x, hand1_y, hand2_x, hand2_y = hand2_x, hand2_y, hand1_x, hand1_y

        pose_x  = pose_x  if pose_x  else [np.nan] * 25
        pose_y  = pose_y  if pose_y  else [np.nan] * 25
        hand1_x = hand1_x if hand1_x else [np.nan] * 21
        hand1_y = hand1_y if hand1_y else [np.nan] * 21
        hand2_x = hand2_x if hand2_x else [np.nan] * 21
        hand2_y = hand2_y if hand2_y else [np.nan] * 21

        pose_points_x.append(pose_x);  pose_points_y.append(pose_y)
        hand1_points_x.append(hand1_x); hand1_points_y.append(hand1_y)
        hand2_points_x.append(hand2_x); hand2_points_y.append(hand2_y)
        n_frames += 1

    cap.release()
    hands.close()
    pose.close()
    return (pose_points_x, pose_points_y,
            hand1_points_x, hand1_points_y,
            hand2_points_x, hand2_points_y,
            n_frames)


def _process_video_new(path, save_dir):
    """Implementation using new MediaPipe Tasks API (>=0.10.10)."""
    hand_opts = mp_vision.HandLandmarkerOptions(
        base_options=mp_tasks.BaseOptions(model_asset_path=_HAND_MODEL),
        num_hands=2,
        min_hand_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        running_mode=mp_vision.RunningMode.VIDEO,
    )
    pose_opts = mp_vision.PoseLandmarkerOptions(
        base_options=mp_tasks.BaseOptions(model_asset_path=_POSE_MODEL),
        min_pose_detection_confidence=0.5,
        min_tracking_confidence=0.5,
        running_mode=mp_vision.RunningMode.VIDEO,
    )

    pose_points_x, pose_points_y = [], []
    hand1_points_x, hand1_points_y = [], []
    hand2_points_x, hand2_points_y = [], []
    n_frames = 0

    if not os.path.isfile(path):
        warnings.warn(path + " file not found")

    cap = cv2.VideoCapture(path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    with mp_vision.HandLandmarker.create_from_options(hand_opts) as hand_det, \
         mp_vision.PoseLandmarker.create_from_options(pose_opts) as pose_det:

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            ts_ms = int(n_frames * 1000 / fps)

            hand_res = hand_det.detect_for_video(mp_image, ts_ms)
            pose_res = pose_det.detect_for_video(mp_image, ts_ms)

            # Pose landmarks (first 25 upper-body points)
            if pose_res.pose_landmarks:
                lms = pose_res.pose_landmarks[0]
                pose_x = [lm.x for lm in lms][:25]
                pose_y = [lm.y for lm in lms][:25]
            else:
                pose_x, pose_y = [np.nan]*25, [np.nan]*25

            # Hand landmarks
            h1_x = h1_y = h2_x = h2_y = None
            if hand_res.hand_landmarks:
                h1_x = [lm.x for lm in hand_res.hand_landmarks[0]]
                h1_y = [lm.y for lm in hand_res.hand_landmarks[0]]
                if len(hand_res.hand_landmarks) > 1:
                    h2_x = [lm.x for lm in hand_res.hand_landmarks[1]]
                    h2_y = [lm.y for lm in hand_res.hand_landmarks[1]]

            # Swap hands using pose wrist landmarks
            if h1_x and not h2_x:
                if swap_hands((pose_x[15], pose_y[15]), (pose_x[16], pose_y[16]),
                              (h1_x[0], h1_y[0]), "h1"):
                    h1_x, h1_y, h2_x, h2_y = [], [], h1_x, h1_y
            elif not h1_x and h2_x:
                if swap_hands((pose_x[15], pose_y[15]), (pose_x[16], pose_y[16]),
                              (h2_x[0], h2_y[0]), "h2"):
                    h1_x, h1_y, h2_x, h2_y = h2_x, h2_y, [], []

            h1_x = h1_x if h1_x else [np.nan]*21
            h1_y = h1_y if h1_y else [np.nan]*21
            h2_x = h2_x if h2_x else [np.nan]*21
            h2_y = h2_y if h2_y else [np.nan]*21

            pose_points_x.append(pose_x);  pose_points_y.append(pose_y)
            hand1_points_x.append(h1_x);   hand1_points_y.append(h1_y)
            hand2_points_x.append(h2_x);   hand2_points_y.append(h2_y)
            n_frames += 1

    cap.release()
    return (pose_points_x, pose_points_y,
            hand1_points_x, hand1_points_y,
            hand2_points_x, hand2_points_y,
            n_frames)


def process_video(path, save_dir):
    label = path.replace("\\", "/").split("/")[-2]
    label = "".join([i for i in label if i.isalpha()]).lower()
    uid   = "_".join([label, os.path.splitext(os.path.basename(path))[0]])

    if _USE_LEGACY:
        result = _process_video_legacy(path, save_dir)
    else:
        result = _process_video_new(path, save_dir)

    (pose_points_x, pose_points_y,
     hand1_points_x, hand1_points_y,
     hand2_points_x, hand2_points_y,
     n_frames) = result

    pose_points_x  = pose_points_x  if pose_points_x  else [[np.nan]*25]
    pose_points_y  = pose_points_y  if pose_points_y  else [[np.nan]*25]
    hand1_points_x = hand1_points_x if hand1_points_x else [[np.nan]*21]
    hand1_points_y = hand1_points_y if hand1_points_y else [[np.nan]*21]
    hand2_points_x = hand2_points_x if hand2_points_x else [[np.nan]*21]
    hand2_points_y = hand2_points_y if hand2_points_y else [[np.nan]*21]

    save_data = {
        "uid": uid, "label": label,
        "pose_x": pose_points_x, "pose_y": pose_points_y,
        "hand1_x": hand1_points_x, "hand1_y": hand1_points_y,
        "hand2_x": hand2_points_x, "hand2_y": hand2_points_y,
        "n_frames": n_frames,
    }
    with open(os.path.join(save_dir, f"{uid}.json"), "w") as f:
        json.dump(save_data, f)

    del save_data
    gc.collect()


def load_file(path, include_dir):
    with open(path, "r") as fp:
        data = fp.read()
        data = data.split("\n")
    data = list(map(lambda x: os.path.join(include_dir, x), data))
    return data


def load_train_test_val_paths(args):
    train_paths = load_file(
        f"train_test_paths/{args.dataset}_train.txt", args.include_dir
    )
    val_paths = load_file(f"train_test_paths/{args.dataset}_val.txt", args.include_dir)
    test_paths = load_file(
        f"train_test_paths/{args.dataset}_test.txt", args.include_dir
    )
    return train_paths, val_paths, test_paths


def save_keypoints(dataset, file_paths, mode):
    save_dir = os.path.join(args.save_dir, f"{dataset}_{mode}_keypoints")
    if not os.path.exists(save_dir):
        os.mkdir(save_dir)

    Parallel(n_jobs=n_cores, backend="multiprocessing")(
        delayed(process_video)(path, save_dir)
        for path in tqdm(file_paths, desc=f"processing {mode} videos")
    )

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate keypoints from Mediapipe")
    parser.add_argument(
        "--include_dir",
        default="",
        type=str,
        required=True,
        help="path to the location of INCLUDE/INCLUDE50 videos",
    )
    parser.add_argument(
        "--save_dir",
        default="",
        type=str,
        required=True,
        help="location to output json file",
    )
    parser.add_argument(
        "--dataset", default="include", type=str, help="options: include or include50"
    )
    args = parser.parse_args()

    n_cores = multiprocessing.cpu_count()
    train_paths, val_paths, test_paths = load_train_test_val_paths(args)

    save_keypoints(args.dataset, val_paths, "val")
    save_keypoints(args.dataset, test_paths, "test")
    save_keypoints(args.dataset, train_paths, "train")
