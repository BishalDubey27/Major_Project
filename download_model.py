"""
Downloads the CNN+LSTM model from HuggingFace Hub at startup.
Set HF_MODEL_REPO env var to your model repo, e.g. 'YourUsername/ISL-INCLUDE-CNN-LSTM'
"""
import os

def download_model_if_needed():
    model_path = 'INCLUDE/cnn_augs_lstm.pth'
    if os.path.exists(model_path):
        return  # already present

    hf_repo = os.environ.get('HF_MODEL_REPO', '')
    if not hf_repo:
        print("HF_MODEL_REPO not set — model must be present locally")
        return

    print(f"Downloading model from {hf_repo}...")
    try:
        from huggingface_hub import hf_hub_download
        path = hf_hub_download(
            repo_id=hf_repo,
            filename='cnn_augs_lstm.pth',
            local_dir='INCLUDE'
        )
        print(f"Model downloaded to {path}")
    except Exception as e:
        print(f"Failed to download model: {e}")

if __name__ == '__main__':
    download_model_if_needed()
