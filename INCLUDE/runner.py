import argparse
import train_nn

parser = argparse.ArgumentParser(description="INCLUDE trainer")
parser.add_argument("--seed", default=0, type=int)
parser.add_argument("--dataset", default="include50", type=str)
parser.add_argument("--use_augs", action="store_true")
parser.add_argument("--use_cnn", action="store_true")
parser.add_argument("--model", default="transformer", type=str)
parser.add_argument("--data_dir", required=True, type=str, help="keypoints dir (no CNN) or CNN features dir (with CNN)")
parser.add_argument("--keypoints_dir", default=None, type=str, help="keypoints dir when using CNN (optional)")
parser.add_argument("--save_path", default="./", type=str)
parser.add_argument("--epochs", default=50, type=int)
parser.add_argument("--batch_size", default=128, type=int)
parser.add_argument("--learning_rate", default=1e-4, type=float)
parser.add_argument("--transformer_size", default="small", type=str)
args = parser.parse_args()

if __name__ == "__main__":
    if args.use_cnn and args.keypoints_dir:
        # Extract CNN features from keypoints into data_dir
        import argparse as ap
        cnn_args = ap.Namespace(**vars(args))
        cnn_args.data_dir = args.keypoints_dir  # read keypoints from here
        from cnn_runner import save_cnn_features
        print("### Extracting CNN features ###")
        save_cnn_features(cnn_args)

    print("### Starting training ###")
    save_path = train_nn.fit(args)
    print("### Evaluating ###")
    train_nn.evaluate(args)
