import pandas as pd, numpy as np, json, torch, sys, glob, os
sys.path.insert(0, '.')
sys.path.insert(0, 'INCLUDE')

# Use dataset.py directly
from INCLUDE.dataset import KeypointsDataset

with open('INCLUDE/label_maps/label_map_include50.json') as f:
    label_map = json.load(f)
idx_to_label = {v: k for k, v in label_map.items()}

from INCLUDE.models.transformer import Transformer
from INCLUDE.configs import TransformerConfig
checkpoint = torch.load('INCLUDE/include50_no_cnn_transformer_large.pth', map_location='cpu', weights_only=False)
config = TransformerConfig(size='large')
model = Transformer(config=config, n_classes=len(label_map))
model.load_state_dict(checkpoint['model'])
model.eval()
print('Model loaded, score:', round(checkpoint['score'], 4))

# Use the actual dataset class
ds = KeypointsDataset(
    keypoints_dir='INCLUDE/keypoints/include50_test_keypoints/include50_test_keypoints',
    use_augs=False,
    label_map=label_map,
    mode='test',
    max_frame_len=200,
)
print('Dataset size:', len(ds))

correct = 0
total = min(30, len(ds))
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

def combine_xy(x, y):
    x, y = np.array(x), np.array(y)
    _, length = x.shape
    x = x.reshape((-1, length, 1))
    y = y.reshape((-1, length, 1))
    return np.concatenate((x, y), -1).astype(np.float32)

def interpolate(arr, fw=1920, fl=1080):
    arr_x = pd.DataFrame(arr[:,:,0]).interpolate(method='linear', limit_direction='both').to_numpy()
    arr_y = pd.DataFrame(arr[:,:,1]).interpolate(method='linear', limit_direction='both').to_numpy()
    if np.count_nonzero(~np.isnan(arr_x)) == 0: arr_x = np.zeros(arr_x.shape)
    if np.count_nonzero(~np.isnan(arr_y)) == 0: arr_y = np.zeros(arr_y.shape)
    return np.stack([arr_x*fw, arr_y*fl], axis=-1)

files = glob.glob('INCLUDE/keypoints/include50_test_keypoints/include50_test_keypoints/*.json')[:30]
correct = 0
for f in files:
    row = pd.read_json(f, typ='series')
    true_label = row.label
    pose = interpolate(combine_xy(row.pose_x, row.pose_y))
    h1   = interpolate(combine_xy(row.hand1_x, row.hand1_y))
    h2   = interpolate(combine_xy(row.hand2_x, row.hand2_y))
    data = np.concatenate([pose.reshape(-1,50), h1.reshape(-1,42), h2.reshape(-1,42)], axis=-1)
    data = np.pad(data, ((0, 200-data.shape[0]),(0,0)), 'constant')
    mean, std = data.mean(), data.std()+1e-8
    data = np.nan_to_num((data-mean)/std, nan=0.0)
    tensor = torch.FloatTensor(data).unsqueeze(0)
    with torch.no_grad():
        probs = torch.softmax(model(tensor), dim=-1)
        conf, pred = probs.max(dim=-1)
    predicted = idx_to_label[pred.item()]
    ok = true_label == predicted
    if ok: correct += 1
    status = "OK" if ok else "WRONG"
    print(f"{true_label:20s} -> {predicted:20s} conf={conf.item():.2f} {status}")

print(f"\nAccuracy: {correct}/{len(files)} = {correct/len(files)*100:.1f}%")
