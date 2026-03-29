import os
import json
import torch
import torch.nn.functional as F
from torch.utils import data
from sklearn.metrics import accuracy_score
from tqdm import tqdm

from models import Transformer
from configs import TransformerConfig
from utils import seed_everything, AverageMeter, EarlyStopping, load_json, get_experiment_name
from dataset import KeypointsDataset

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def train(dataloader, model, optimizer, device):
    model.train()
    losses = AverageMeter()
    accuracy = AverageMeter()
    pbar = tqdm(dataloader, desc="Training")
    for batch in pbar:
        input_data = batch["data"].to(device)
        label = batch["label"].to(device)
        optimizer.zero_grad()
        preds = model(input_data)
        loss = F.cross_entropy(preds, label, label_smoothing=0.1)
        loss.backward()
        optimizer.step()
        losses.update(loss.item())
        preds = preds.detach().cpu()
        accuracy.update(accuracy_score(
            label.cpu().numpy(),
            torch.argmax(torch.softmax(preds, dim=-1), dim=-1).numpy()
        ))
        pbar.set_postfix(loss=losses.avg, accuracy=accuracy.avg)
    torch.cuda.empty_cache()
    return losses.avg, accuracy.avg


@torch.no_grad()
def validate(dataloader, model, device):
    model.eval()
    losses = AverageMeter()
    accuracy = AverageMeter()
    pbar = tqdm(dataloader, desc="Eval")
    for batch in pbar:
        input_data = batch["data"].to(device)
        label = batch["label"].to(device)
        preds = model(input_data)
        loss = F.cross_entropy(preds, label)
        losses.update(loss.item())
        preds = preds.detach().cpu()
        accuracy.update(accuracy_score(
            label.cpu().numpy(),
            torch.argmax(torch.softmax(preds, dim=-1), dim=-1).numpy()
        ))
        pbar.set_postfix(loss=losses.avg, accuracy=accuracy.avg)
    torch.cuda.empty_cache()
    return losses.avg, accuracy.avg


def fit(args):
    seed_everything(args.seed)

    label_map = load_json(f"label_maps/label_map_{args.dataset}.json")
    n_classes = len(label_map)

    if args.use_cnn:
        from configs import CnnConfig
        from dataset import FeaturesDatset
        from models import LSTM
        from configs import LstmConfig
        lstm_config = LstmConfig()
        lstm_config.input_size = CnnConfig.output_dim  # 1280
        model = LSTM(config=lstm_config, n_classes=n_classes).to(device)
        train_dir = os.path.join(args.data_dir, f"{args.dataset}_train_cnn_features")
        val_dir   = os.path.join(args.data_dir, f"{args.dataset}_val_cnn_features")
        train_ds  = FeaturesDatset(train_dir, label_map=label_map, mode="train")
        val_ds    = FeaturesDatset(val_dir,   label_map=label_map, mode="val")
    else:
        config = TransformerConfig(size=args.transformer_size)
        model = Transformer(config=config, n_classes=n_classes).to(device)
        train_dir = os.path.join(args.data_dir, f"{args.dataset}_train_keypoints")
        val_dir   = os.path.join(args.data_dir, f"{args.dataset}_val_keypoints")
        train_ds  = KeypointsDataset(train_dir, use_augs=args.use_augs, label_map=label_map, mode="train")
        val_ds    = KeypointsDataset(val_dir,   use_augs=False,          label_map=label_map, mode="val")

    train_loader = data.DataLoader(train_ds, batch_size=args.batch_size, shuffle=True,  num_workers=2)
    val_loader   = data.DataLoader(val_ds,   batch_size=args.batch_size, shuffle=False, num_workers=2)

    optimizer = torch.optim.Adam(model.parameters(), lr=args.learning_rate)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs)

    exp_name = get_experiment_name(args)
    os.makedirs(args.save_path, exist_ok=True)
    save_path = os.path.join(args.save_path, f"{exp_name}.pth")

    early_stopping = EarlyStopping(patience=10, mode="max")

    for epoch in range(args.epochs):
        print(f"\nEpoch {epoch+1}/{args.epochs}")
        train_loss, train_acc = train(train_loader, model, optimizer, device)
        val_loss, val_acc     = validate(val_loader, model, device)
        scheduler.step()

        print(f"Train loss: {train_loss:.4f}  acc: {train_acc:.4f}")
        print(f"Val   loss: {val_loss:.4f}    acc: {val_acc:.4f}")

        early_stopping(save_path, val_acc, model, optimizer, scheduler)
        if early_stopping.early_stop:
            print("Early stopping triggered")
            break

    print(f"\nTraining complete. Best val accuracy: {early_stopping.val_score:.4f}")
    return save_path


def evaluate(args):
    label_map = load_json(f"label_maps/label_map_{args.dataset}.json")
    n_classes = len(label_map)

    exp_name = get_experiment_name(args)
    save_path = os.path.join(args.save_path, f"{exp_name}.pth")
    checkpoint = torch.load(save_path, map_location=device, weights_only=False)

    if args.use_cnn:
        from configs import CnnConfig, LstmConfig
        from dataset import FeaturesDatset
        from models import LSTM
        lstm_config = LstmConfig()
        lstm_config.input_size = CnnConfig.output_dim
        model = LSTM(config=lstm_config, n_classes=n_classes).to(device)
        test_dir = os.path.join(args.data_dir, f"{args.dataset}_test_cnn_features")
        test_ds  = FeaturesDatset(test_dir, label_map=label_map, mode="test")
    else:
        config = TransformerConfig(size=args.transformer_size)
        model = Transformer(config=config, n_classes=n_classes).to(device)
        test_dir = os.path.join(args.data_dir, f"{args.dataset}_test_keypoints")
        test_ds  = KeypointsDataset(test_dir, use_augs=False, label_map=label_map, mode="test")

    model.load_state_dict(checkpoint["model"])
    test_loader = data.DataLoader(test_ds, batch_size=args.batch_size, shuffle=False, num_workers=2)
    _, test_acc = validate(test_loader, model, device)
    print(f"Test accuracy: {test_acc:.4f}")
    return test_acc
