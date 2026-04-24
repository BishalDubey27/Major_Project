import json

with open('INCLUDE_Retrain_81pct_Colab.ipynb', encoding='utf-8') as f:
    nb = json.load(f)

new_reextract = (
    "# Step 3b: Re-extract keypoints from INCLUDE zip files on Google Drive\n"
    "# Upload your INCLUDE zip files to Drive, then set the paths below\n"
    "# More videos = better accuracy\n\n"
    "import zipfile, os, glob, sys, multiprocessing\n\n"
    "# ── Set these paths to your zip files on Drive ───────────────────────\n"
    "DRIVE_ZIP_TRAIN = '/content/drive/MyDrive/include_train.zip'\n"
    "DRIVE_ZIP_VAL   = '/content/drive/MyDrive/include_val.zip'\n"
    "DRIVE_ZIP_TEST  = '/content/drive/MyDrive/include_test.zip'\n"
    "# If you have a single zip with all splits:\n"
    "# DRIVE_ZIP_ALL = '/content/drive/MyDrive/include_all.zip'\n\n"
    "# Where to save new keypoints on Drive\n"
    "DRIVE_NEW_KP = '/content/drive/MyDrive/keypoints_new'\n\n"
    "# ── Extract zips ─────────────────────────────────────────────────────\n"
    "os.makedirs('/content/include_videos', exist_ok=True)\n"
    "for zip_path, split in [\n"
    "    (DRIVE_ZIP_TRAIN, 'train'),\n"
    "    (DRIVE_ZIP_VAL,   'val'),\n"
    "    (DRIVE_ZIP_TEST,  'test')\n"
    "]:\n"
    "    if os.path.exists(zip_path):\n"
    "        print(f'Extracting {split} zip...')\n"
    "        with zipfile.ZipFile(zip_path, 'r') as z:\n"
    "            z.extractall(f'/content/include_videos/{split}')\n"
    "        n = len(glob.glob(f'/content/include_videos/{split}/**/*.mp4', recursive=True))\n"
    "        print(f'  {split}: {n} videos extracted')\n"
    "    else:\n"
    "        print(f'  {split} zip not found: {zip_path}')\n\n"
    "# ── Generate keypoints ────────────────────────────────────────────────\n"
    "sys.path.insert(0, '/content/Major_Project/INCLUDE')\n"
    "from generate_keypoints import process_video\n"
    "from joblib import Parallel, delayed\n"
    "from tqdm import tqdm\n\n"
    "os.makedirs(DRIVE_NEW_KP, exist_ok=True)\n"
    "n_cores = min(2, multiprocessing.cpu_count())\n\n"
    "for split in ['train', 'val', 'test']:\n"
    "    video_dir = f'/content/include_videos/{split}'\n"
    "    if not os.path.exists(video_dir):\n"
    "        print(f'Skipping {split} - no videos')\n"
    "        continue\n"
    "    # Videos organized as: split/class_name/video.mp4\n"
    "    video_paths = glob.glob(f'{video_dir}/**/*.mp4', recursive=True)\n"
    "    if not video_paths:\n"
    "        video_paths = glob.glob(f'{video_dir}/**/*.avi', recursive=True)\n"
    "    save_dir = os.path.join(DRIVE_NEW_KP, f'include_{split}_keypoints')\n"
    "    os.makedirs(save_dir, exist_ok=True)\n"
    "    print(f'Processing {len(video_paths)} {split} videos...')\n"
    "    Parallel(n_jobs=n_cores)(\n"
    "        delayed(process_video)(p, save_dir)\n"
    "        for p in tqdm(video_paths, desc=split)\n"
    "    )\n"
    "    n_kp = len(glob.glob(f'{save_dir}/*.json'))\n"
    "    print(f'  {split}: {n_kp} keypoints saved to Drive')\n\n"
    "print()\n"
    "print('Done! New keypoints saved to:', DRIVE_NEW_KP)\n"
    "print('Now update DRIVE_TRAIN/VAL/TEST in Step 3 to point to the new folders')\n"
    "print('Then re-run from Step 3 to train with more data')"
)

# Find and replace the re-extraction cell
for i, cell in enumerate(nb['cells']):
    if cell['cell_type'] == 'code':
        src = cell['source'][0] if isinstance(cell['source'], list) else cell['source']
        if 'Re-extract keypoints' in src or 'OPTIONAL' in src or 'Keypoint re-extraction' in src:
            if isinstance(cell['source'], list):
                cell['source'][0] = new_reextract
            else:
                cell['source'] = new_reextract
            print(f'Updated re-extraction cell at index {i}')
            break

with open('INCLUDE_Retrain_81pct_Colab.ipynb', 'w', encoding='utf-8') as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
print('Done')
