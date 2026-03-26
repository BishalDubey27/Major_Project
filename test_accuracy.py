import pandas as pd, numpy as np, json, torch, sys, glob, os
sys.path.insert(0, '.')
sys.path.insert(0, 'INCLUDE')

from INCLUDE.dataset import KeypointsDataset
from INCLUDE.models.transformer import Transformer
from INCLUDE.configs import TransformerConfig

with open('INCLUDE/label_maps/label_map_include50.json') as f:
    label_map = json.load(f)
idx_to_label = {v: k for k, v in label_map.items()}

checkpoint = torch.load('INCLUDE/augs_transformer (1).pth', map_location='cpu', weights_only=False)
config = TransformerConfig(size='small')
model = Transformer(config=config, n_classes=len(label_map))
model.load_state_dict(checkpoint['model'])
model.eval()
print('Model loaded, score:', round(checkpoint['score'], 4))

ds = KeypointsDataset(
    keypoints_dir='INCLUDE/keypoints/include50_test_keypoints',
    use_augs=False, label_map=label_map, mode='test', max_frame_len=200,
)
print('Dataset size:', len(ds))

correct = 0
total = min(50, len(ds))
for i in range(total):
    sample = ds[i]
    tensor = sample['data'].unsqueeze(0)
    true_label = sample['lablel_string']
    with torch.no_grad():
        probs = torch.softmax(model(tensor), dim=-1)
        conf, pred = probs.max(dim=-1)
    predicted = idx_to_label[pred.item()]
    ok = true_label == predicted
    if ok: correct += 1
    status = "OK" if ok else "WRONG"
    print(f"{true_label:20s} -> {predicted:20s} conf={conf.item():.2f} {status}")

print(f"\nAccuracy: {correct}/{total} = {correct/total*100:.1f}%")
